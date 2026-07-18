from fastmcp import Client
import ollama
from dotenv import load_dotenv
import os
import re
import json
from pathlib import Path

load_dotenv()

class LocalMCPClient:
    def __init__(self):
        # Configuraciones para el LLM local con Ollama
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Ruta del servidor MCP objetivo (tomada de tu anthropic_client.py)
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

    async def get_tools_for_llm(self):
        """Convierte herramientas MCP a formato LLM compatible con Ollama/OpenAI"""
        async with await self._get_mcp_client() as Cliente:
            tools = await Cliente.list_tools()

            llm_tools = []
            for tool in tools:
                llm_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema
                    }
                })

            return llm_tools, Cliente
    
    async def get_resources_as_tools(self):
        """Encapsula recursos y plantillas como herramientas formato OpenAI/Ollama"""
        async with await self._get_mcp_client() as Cliente:
            resources = await Cliente.list_resources()
            templates = await Cliente.list_resource_templates()

            resource_tools = []
            resource_map = {}

            # 1. Recursos estáticos
            for resource in resources:
                uri = str(resource.uri)
                # Limpieza estricta de nombre para modelos locales
                func_name = f"get_res_{re.sub(r'[^a-zA-Z0-9]', '_', uri)}"

                resource_tools.append({
                    "type": "function", 
                    "function": {
                        "name": func_name,
                        "description": resource.description or f"Lee el recurso {uri}",
                        "parameters": { 
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                })
                resource_map[func_name] = {"uri": uri}
            
            # 2. Plantillas de recursos
            for template in templates:
                uri_template = str(template.uriTemplate)
                
                # Sanitizar nombre del template
                func_name = f"tpl_{re.sub(r'[^a-zA-Z0-9]', '_', template.name)}"

                params = re.findall(r'\{(\w+)\}', uri_template)
                properties = {p: {"type": "string", "description": f"Valor para {p}"} for p in params}

                resource_tools.append({
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "description": template.description or f"Usa la plantilla {uri_template}",
                        "parameters": { 
                            "type": "object",
                            "properties": properties,
                            "required": params
                        }
                    }
                })
                resource_map[func_name] = {"template": uri_template, "params": params}

            return resource_tools, resource_map
    
    async def get_prompt_messages(self, prompt_name: str, **kwargs) -> str:
        """Obtiene el mensaje de un prompt específico"""
        async with await self._get_mcp_client() as Cliente:
            prompt = await Cliente.get_prompt(prompt_name, arguments=kwargs)
            return json.loads(prompt.messages[0].content.text)

    async def call_tool(self, tool_name: str, arguments: dict, client):
        """Ejecuta una herramienta MCP"""
        result = await client.call_tool(tool_name, arguments)
        # Verificar la estructura de la respuesta
        if result and result.content and len(result.content) > 0:
            if hasattr(result.content[0], 'text'):
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
        """Procesa una conversación con un LLM usando MCP y Ollama"""
        async with await self._get_mcp_client() as mcp:
            # 1. PREPARAR 'MENÚ' DE HERRAMIENTAS
            # Obtener herramientas y recursos formateados para Ollama
            tools, _ = await self.get_tools_for_llm()
            resource_tools, resource_map = await self.get_resources_as_tools()
            all_tools = tools + resource_tools

            # 2. PRIMERA LLAMADA A OLLAMA
            response = ollama.chat(
                model=self.ollama_model,
                messages=messages,
                tools=all_tools,
            )

            response_message = response['message']
            tool_calls = response_message.get('tool_calls', [])

            # 3. ANALIZAR LA RESPUESTA
            # Si el LLM no llamó a ninguna herramienta, retornamos su texto directamente
            if not tool_calls:
                return response_message.get('content', '')

            # Si hay llamadas a herramientas, guardamos la intención en el historial
            messages.append({
                "role": "assistant",
                "content": response_message.get('content', ''),
                "tool_calls": tool_calls
            })

            # Procesar cada herramienta solicitada por el LLM
            for tool_call in tool_calls:
                function_name = tool_call['function']['name']
                function_args = tool_call['function']['arguments']

                if not function_name:
                    print("Advertencia: El LLM intentó usar una herramienta sin nombre.")
                    continue

                # Verificar si lo que pidió es un recurso (mapeado previamente)
                if function_name in resource_map:
                    resource_info = resource_map[function_name]

                    if "template" in resource_info:
                        # Es una plantilla de recurso: construir URI con los argumentos
                        uri = resource_info["template"]
                        for param in resource_info["params"]:
                            uri = uri.replace(f"{{{param}}}", str(function_args.get(param, "")))
                    else:
                        # Es un recurso estático
                        uri = resource_info["uri"]

                    print(f"[{self.ollama_model}] Solicitando recurso: {uri}")
                    function_response = await self.get_resource(uri, mcp)
                else:
                    # Es una herramienta MCP normal
                    print(f"[{self.ollama_model}] Ejecutando herramienta: {function_name}")
                    function_response = await self.call_tool(function_name, function_args, mcp)
                
                # Añadir el resultado de la herramienta al contexto de los mensajes
                messages.append({
                    "role": "tool",
                    "content": str(function_response),
                    "name": function_name,
                })

            # 4. SEGUNDA LLAMADA A OLLAMA
            # Volvemos a llamar al LLM, ahora con los resultados de las herramientas
            second_response = ollama.chat(
                model=self.ollama_model,
                messages=messages,
            )

            return second_response['message'].get('content', '')