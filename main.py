from bedrock_agentcore import BedrockAgentCoreApp
from agent import compliance_agent

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    prompt = payload.get(
        "prompt",
        "Analyze documents/demo-contract.txt for GDPR compliance and save a report."
    )
    result = compliance_agent(prompt)
    return {"result": str(result)}

if __name__ == "__main__":
    app.run()