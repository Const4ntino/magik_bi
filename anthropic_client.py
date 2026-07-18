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

    async def chat(self, messages: list):
            """Procesa una conversación con streaming y soporte multi-turno de herramientas MCP"""
            async with await self._get_mcp_client() as mcp:
                # 1. PREPARAR HERRAMIENTAS
                tools_normales, _ = await self.get_tools_for_anthropic()
                resource_tools, resource_map = await self.get_resources_as_tools()
                all_tools = tools_normales + resource_tools

                while True:
                    # 2. SEÑALAR INICIO DE LLAMADA / RESET EN ESTE TURNO
                    tool_requests = []
                    
                    # Usamos el contexto .stream() de Anthropic
                    async with self.anthropic_client.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=2000,
                        messages=messages,
                        tools=all_tools
                    ) as stream:
                        
                        # Iteramos sobre los fragmentos del stream a medida que llegan
                        async for text in stream.text_stream:
                            yield text  # <--- Esto envía el texto en tiempo real a tu interfaz

                        # Al finalizar el stream, recuperamos el mensaje completo finalizado
                        final_message = await stream.get_final_message()

                    # 3. PREPARAR HISTORIAL (Igual que tu código original, pero usando final_message)
                    assistant_message_content = []
                    for content_block in final_message.content:
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

                    # Si Claude NO pidió herramientas, el turno del chat ha terminado por completo
                    if not tool_requests:
                        return

                    # 4. EJECUCIÓN DE HERRAMIENTAS MCP (Si Claude las solicitó)
                    tool_results_content = []
                    for tool_block in tool_requests:
                        tool_name = tool_block.name
                        tool_args = tool_block.input

                        if tool_name in resource_map:
                            info = resource_map[tool_name]
                            uri = info.get("uri")
                            if "template" in info:
                                uri = info["template"]
                                for p in info.get("params", []):
                                    uri = uri.replace(f"{{{p}}}", str(tool_args.get(p, "")))
                            result_data = await self.get_resource(uri, mcp)
                        else:
                            result_data = await self.call_tool(tool_name, tool_args, mcp)

                        tool_results_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": str(result_data)
                        })

                    # Añadimos los resultados al historial para que el bucle `while True` 
                    # vuelva a llamar a Claude con los datos de la herramienta.
                    messages.append({
                        "role": "user",
                        "content": tool_results_content
                    })