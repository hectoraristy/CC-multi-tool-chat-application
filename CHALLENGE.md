# Coding Challenge: Multi-Tool Chat Application

Build a full-stack chat application with frontend and backend components, provisioned on AWS using Terraform, and implemented with Python, LangGraph, and Pants.

The solution should include a React-based frontend that communicates with a backend API, enabling users to interact with an AI agent capable of calling multiple tools.

## Core Requirement

The system must support a chat experience where an agent can call tools. At minimum, it must include:

### Session Manager Tool (Required)

A chat session mechanism that allows the agent to call tools and store tool results in a secondary datastore. The agent should be able to use metadata from stored results to decide whether a result should be brought back into the context window in future interactions.

### Tool Integration Framework

The architecture should allow multiple tools to be integrated, such as:

- Database queries
- Web downloads
- External API calls
- File-based sources (e.g., CSV files from storage)

## Nice-to-Have (Optional)

### Summarization Sub-Agent

A secondary agent or workflow that processes oversized tool results when they are too large to fit into the context window.

If implementing this fully within one working week is not feasible, provide a design proposal explaining how it would be implemented.

## Technical Expectations

- **Full-stack solution**
- **Frontend:** React application
- **Backend:** Python API
- **Agent framework:** LangGraph
- **Build system:** Pants
- **Infrastructure:** AWS provisioned using Terraform
- API integration between frontend and backend

## Timeline

We expect a submission within 1 working week, and the sooner the better.

## Deliverables

Please submit:

- A demo video showing the application running and explaining the architecture
- The source repository with a clear README
- A design document describing:
  - Architecture
  - Key technical decisions
  - Trade-offs
  - Any incomplete features or proposed designs (if applicable)

## Notes

- Focus on clear architecture and maintainable code
- Make reasonable assumptions when necessary
- We are primarily evaluating engineering thinking, system design, and implementation quality
