import asyncio
import gradio as gr
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context
from llama_index.llms.ollama import Ollama

# Initialize the LLM
llm = Ollama(
    model="qwen3:0.6b",
    request_timeout=600
)

# MCP client and tools
mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
mcp_tools = McpToolSpec(client=mcp_client)

# System prompt for the agent
SYSTEM_PROMPT = """\
You are an AI assistant for tool calling for a smart TV control.
Work with tools to perform the required actions and ask the user for any missing parameters if required.
"""

# Global variables to store agent and context
agent = None
agent_context = None

# Define async function to get the agent
async def get_agent(tools: McpToolSpec) -> FunctionAgent:
    tools = await tools.to_tool_list_async()
    agent = FunctionAgent(
        name="Agent",
        description="An agent interacting with a smart TV",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    print("Agent returned successfully")
    return agent

# Define async function to handle user messages
async def handle_user_message(
    message_content: str,
    agent: FunctionAgent,
    agent_context: Context,
    verbose: bool = False,
):
    handler = agent.run(message_content, ctx=agent_context)
    print("Agent ran")
    
    # Collect tool call information for verbose output
    tool_calls = []
    
    async for event in handler.stream_events():
        if verbose and isinstance(event, ToolCall):
            tool_info = f"Calling tool {event.tool_name} with kwargs {event.tool_kwargs}"
            tool_calls.append(tool_info)
            print(tool_info)
        elif verbose and isinstance(event, ToolCallResult):
            tool_info = f"Tool {event.tool_name} returned {event.tool_output}"
            tool_calls.append(tool_info)
            print(tool_info)
    
    response = await handler
    return str(response), tool_calls

# Initialize agent on startup
async def initialize_agent():
    global agent, agent_context
    agent = await get_agent(mcp_tools)
    agent_context = Context(agent)
    return "Agent initialized successfully!"

# Gradio chat function
async def chat_with_agent(message, history):
    global agent, agent_context
    
    # Initialize agent if not already done
    if agent is None or agent_context is None:
        await initialize_agent()
    
    # Get response from agent
    response, tool_calls = await handle_user_message(message, agent, agent_context, verbose=True)
    
    # Add tool call information to response if any
    if tool_calls:
        tool_info = "\n\n**Tool Calls:**\n" + "\n".join(f"- {call}" for call in tool_calls)
        response += tool_info
    
    return response

# Create Gradio interface
def create_gradio_interface():
    with gr.Blocks(title="Smart TV Control Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 📺 Smart TV Control Agent")
        gr.Markdown("Chat with your AI assistant to control your smart TV using natural language commands.")
        
        chatbot = gr.Chatbot(
            height=500,
            placeholder="Agent responses will appear here...",
            show_copy_button=True
        )
        
        msg = gr.Textbox(
            placeholder="Type your TV control command here... (e.g., 'Play Netflix', 'Increase volume', 'Turn on the TV')",
            container=False,
            scale=7
        )
        
        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary", scale=1)
            clear_btn = gr.Button("Clear Chat", scale=1)
        
        # Status indicator
        status = gr.Textbox(
            label="Status",
            value="Ready to initialize agent...",
            interactive=False,
            max_lines=1
        )
        
        # Initialize agent on app load
        demo.load(
            fn=initialize_agent,
            outputs=status
        )
        
        # Handle message submission
        async def submit_message(message, history):
            if not message.strip():
                return history, ""
            
            # Add user message to history
            history.append([message, None])
            
            try:
                # Get agent response
                response = await chat_with_agent(message, history)
                # Update history with agent response
                history[-1][1] = response
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                history[-1][1] = error_msg
                print(f"Error in chat: {e}")
            
            return history, ""
        
        # Event handlers
        submit_btn.click(
            fn=submit_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg],
            show_progress=True
        )
        
        msg.submit(
            fn=submit_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg],
            show_progress=True
        )
        
        clear_btn.click(
            fn=lambda: [],
            outputs=chatbot
        )
        
        # Add some example commands
        with gr.Accordion("💡 Example Commands", open=False):
            gr.Markdown("""
            Try these example commands:
            - "Play a movie on Netflix"
            - "Increase the volume to 50%"
            - "Turn on the TV"
            - "Play some music"
            - "Launch a game"
            - "Install WhatsApp"
            - "What's the weather like?"
            - "Mute the TV"
            """)
    
    return demo

# Main runner function (kept for backward compatibility)
async def main():
    print("Starting Smart TV Control Agent with Gradio UI...")
    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )

# Entry point
if __name__ == "__main__":
    # Run with Gradio UI
    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )