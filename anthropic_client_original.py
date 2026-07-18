from fastmcp import Client
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

class AnthropicMCPClient:
    def __init__(self):
        self.anthropic_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        current_dir = Path(__file__).parent
        self.mcp_server_path = str(current_dir / "mcp_server.py")

    async def _get_mcp_client(self):
        """Crear conexión con el servidor MCP"""
        return Client(self.mcp_server_path)
    
    async def get_system_info(self) -> dict:
        """Información del sistema MCP"""
        async with await self._get_mcp_client() as Cliente:
            tools = await Cliente.list_tools()
            resources = await Cliente.list_resources()
            templates = await Cliente.list_resource_templates()
            prompts = await Cliente.list_prompts()

            return {
                "tools": [t.name for t in tools],
                "resources": [r.name for r in resources],
                "templates": [t.name for t in templates],
                "prompts": [p.name for p in prompts],
                "server": self.mcp_server_path
            }

    async def get_tools_for_anthropic(self):
        """Convierte herramientas MCP a formato Anthropic"""
        async with await self._get_mcp_client() as Cliente:
            tools = await Cliente.list_tools()

            claude_tools = [{
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema
            } for tool in tools]

            return claude_tools, Cliente
    
    async def get_resources_as_tools(self):
        """Encapsula recursos y plantilla de recursos como herramientas"""
        async with await self._get_mcp_client() as Cliente:
            # Obtener recursos y plantilla de recursos
            resources = await Cliente.list_resources()
            templates = await Cliente.list_resource_templates()

            resource_tools = []
            resource_map = {}

            # 1. Recursos estáticos
            for resource in resources:
                uri = str(resource.uri)
                func_name = f"get_resource_{uri.replace('://', '_').replace('/', '_')}"

                resource_tools.append({
                    "name": func_name,
                    "description": resource.description or resource.name,
                    "input_schema": {"type": "object", "properties": {}, "required": []}
                })

                resource_map[func_name] = {"uri": uri}
            
            # 2.  Plantilla de recursos
            for template in templates:
                uri_template = str(template.uriTemplate)
                func_name= template.name

                # Recuperar parámetros del template
                import re
                params = re.findall(r'\{(\w+)\}', uri_template)

                properties = {p: {"type": "string", "description": f"Parametro {p}"} for p in params}

                resource_tools.append({
                    "name": func_name,
                    "description": template.description or template.name,
                    "input_schema": {"type": "object", "properties": properties, "required": params}
                })

                resource_map[func_name] = {"template": uri_template, "params": params}

            return resource_tools, resource_map
    
    async def get_prompt_messages(self, prompt_name: str, **kwargs) -> str:
        """Obtiene el mensaje de un prompt específico"""
        async with await self._get_mcp_client() as Cliente:
            prompt = await Cliente.get_prompt(prompt_name, arguments=kwargs)
            import json
            return json.loads(prompt.messages[0].content.text)

    async def call_tool(self, tool_name: str, arguments: dict, client):
        """Ejecuta una herramienta MCP"""
        result = await client.call_tool(tool_name, arguments)
        # Verificar la estructura de la respuesta
        if result and result.content and len(result.content) > 0:
            if hasattr (result.content[0], 'text'):
                return result.content[0].text
        return "La ejecución de la herramienta no obtuvo resultados"
    
    async def get_resource(self, uri: str, client):
        """Obtiene un recurso MCP"""
        result = await client.read_resource(uri)
        # Verificar la estructura de la respuesta
        if result and len(result) > 0:
            if hasattr(result[0], 'text'):
                return result[0].text
            if hasattr(result[0], 'content'):
                return result[0].content
        return "Recurso no disponible"

    async def chat(self, messages: list) -> str:
        """Procesa una conversación siguiendo el estilo oficial de Anthropic con soporte multi-turno de herramientas"""
        async with await self._get_mcp_client() as mcp:
            # 1. PREPARAR 'MENÚ' DE HERRAMIENTAS
            tools_normales, _ = await self.get_tools_for_anthropic()
            resource_tools, resource_map = await self.get_resources_as_tools()
            all_tools = tools_normales + resource_tools

            # Mantener un bucle activo por si Claude encadena múltiples llamadas a herramientas
            while True:
                # 2. LLAMADA A CLAUDE
                response = await self.anthropic_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2000,
                    messages=messages,
                    tools=all_tools
                )

                # Creamos el contenedor para el mensaje que el asistente va a dejar en el historial
                assistant_message_content = []
                tool_requests = []

                # Analizamos todos los bloques devueltos en este turno
                for content_block in response.content:
                    if content_block.type == 'text':
                        assistant_message_content.append({
                            "type": "text",
                            "text": content_block.text
                        })
                    elif content_block.type == 'tool_use':
                        assistant_message_content.append(content_block.model_dump())
                        tool_requests.append(content_block)

                # Añadimos la respuesta del asistente al historial de mensajes obligatoriamente
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })

                # Si Claude NO pidió usar herramientas en este turno, terminamos el bucle
                if not tool_requests:
                    # Buscamos el bloque de texto para retornar a la interfaz de Shinychat
                    for block in response.content:
                        if block.type == 'text':
                            return block.text
                    return "Procesado correctamente (sin respuesta de texto)."

                # Si llegamos aquí, es porque hay herramientas que ejecutar
                tool_results_content = []
                
                for tool_block in tool_requests:
                    tool_name = tool_block.name
                    tool_args = tool_block.input

                    # --- LÓGICA DE RECURSOS ---
                    if tool_name in resource_map:
                        info = resource_map[tool_name]
                        uri = info.get("uri")
                        if "template" in info:
                            uri = info["template"]
                            for p in info.get("params", []):
                                uri = uri.replace(f"{{{p}}}", str(tool_args.get(p, "")))
                        result_data = await self.get_resource(uri, mcp)
                    else:
                        # Es una Herramienta normal
                        result_data = await self.call_tool(tool_name, tool_args, mcp)
                    # ---------------------------------------

                    # Acumulamos el resultado del tool_use actual
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": str(result_data)
                    })

                # Añadimos los resultados como un mensaje de rol 'user' al historial
                messages.append({
                    "role": "user",
                    "content": tool_results_content
                })
                
                # El bucle 'while True' continuará enviando estos resultados a Claude.
                # Si Claude requiere más herramientas, repetirá el ciclo; si no, irá al bloque 'if not tool_requests:' y devolverá el texto final.


    # # async def chat(self, messages: list) -> str:
    # async def chat(self, messages: list) -> str:
    #     """Procesa una conversación siguiendo el estilo oficial de Anthropic"""
    #     async with await self._get_mcp_client() as mcp:
    #         # 1. PREPARAR 'MENÚ' DE HERRAMIENTAS
    #         # Combinar herramientas normales + recursos convertidos en herramientas
    #         tools_normales, _ = await self.get_tools_for_anthropic()
    #         resource_tools, resource_map = await self.get_resources_as_tools()
    #         all_tools = tools_normales + resource_tools

    #         # 2. PRIMERA LLAMADA A CLAUDE
    #         response = await self.anthropic_client.messages.create(
    #             model="claude-sonnet-4-6",
    #             max_tokens=2000,
    #             messages=messages,
    #             tools=all_tools
    #         )

    #         # 3. ANALIZAR LO QUE DIJO CLAUDE
    #         # Guardar los bloques de la respuesta para el historial
    #         assistant_message_content = []
            
    #         for content_block in response.content:
    #             # Si Claude simplemente escribió
    #             if content_block.type == 'text':
    #                 assistant_message_content.append(content_block)
                    
    #             # Si Claude quiere usar una herramienta (o un recurso)
    #             elif content_block.type == 'tool_use':
    #                 tool_name = content_block.name
    #                 tool_args = content_block.input
                    
    #                 # ---  LÓGICA DE RECURSOS ---
    #                 if tool_name in resource_map:
    #                     # Es un Recurso: Construir la URI
    #                     info = resource_map[tool_name]
    #                     uri = info.get("uri")
    #                     if "template" in info:
    #                         uri = info["template"]
    #                         for p in info.get("params", []):
    #                             uri = uri.replace(f"{{{p}}}", str(tool_args.get(p, "")))
                        
    #                     # Ejecutar la lectura del recurso
    #                     result_data = await self.get_resource(uri, mcp)
    #                 else:
    #                     # Es una Herramienta normal
    #                     result_data = await self.call_tool(tool_name, tool_args, mcp)
    #                 # ---------------------------------------

    #                 # Guardar la intención de Claude en el historial
    #                 assistant_message_content.append(content_block)

    #                 # Añadir al historial el mensaje del Asistente (obligatorio antes del resultado)
    #                 messages.append({
    #                     "role": "assistant",
    #                     "content": assistant_message_content
    #                 })

    #                 # Añadir al historial el RESULTADO de la herramienta
    #                 messages.append({
    #                     "role": "user",
    #                     "content": [
    #                         {
    #                             "type": "tool_result",
    #                             "tool_use_id": content_block.id,
    #                             "content": str(result_data)
    #                         }
    #                     ]
    #                 })

    #                 # 4. SEGUNDA LLAMADA: Dar los resultados a Claude para la respuesta final
    #                 response = await self.anthropic_client.messages.create(
    #                     model="claude-sonnet-4-6",
    #                     max_tokens=2000,
    #                     messages=messages,
    #                     tools=all_tools
    #                 )
    #                 # model="claude-haiku-4-5",
    #                 # Retornar el texto final
    #                 return response.content[0].text

    #         # Si no hubo herramientas, devolver el texto que haya dicho
    #         return response.content[0].text