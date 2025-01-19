# ami0 - AI Machine Interface
This repo contains a POC for an LLM agent framework.
The main features are:
- The [core framework](ami/os.py) of running the observe - think - act loop. 
To ensure the agent is only able to execute valid actions, the *structured output* feature of the OpenAI API is used. 
- A concept of "apps", which the agent can use to observe its environment and manipulate this. 
An implementation of an app consists of subclassing the [`App` class](ami/app.py).
It is mainly characterized by providing a prompt which explains the purpose and usage of the app, a list of possible actions defined as Pydantic models. 
Since these models can be generated dynamically depending on the current state of the app, it is possible to "force" to agent to only take valid actions.

Example apps included are:
- A [text based web browser](ami/apps/browser.py), based on Playwright. 
The browser can navigate to a URL, click on elements and take screenshots.
- A [terminal environment](ami/apps/ssh.py), implemented as a SSH connection to a Docker container (running e.g. Ubuntu). 
A sample Dockerfile is provided.

The agent is able to switch between apps, and can be extended with new apps easily.

## Installation and usage
1. Install python requirements.
I usually create a virtual environment for this.
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
You want to use Python 3.9 or higher.

2. Configure the OpenAI API key.
Create a `.env` file in the root of the project with the following content:
```
OPENAI_API_KEY=sk-proj-...
```

3. Build and run the Docker container.
The Dockerfile has hardcoded credentials for the SSH connection and exposes port 22, 
so probably not a good idea to expose the container to the internet.
```bash
docker build -t ubuntu-ssh .
docker run -d -p 2222:22 ubuntu-ssh
```

4. (Optional) Adjust the system prompt in to the specific use case in [system.md](prompts/system.md).
By default, the agent is tasked to play a [Wiki game](https://en.wikipedia.org/wiki/Wikipedia:Wiki_Game).

5. Start the agent by executing the [run.py](run.py) script. 
You will be prompted to confirm each action the agent wants to take.
By default, the browser window will be rendered, 
but you can also run the agent in headless mode by switching the `BROWSER_HEADLESS` paramter in the `run.py` script.
```bash
python run.py
```

## Roadmap
- [ ] **Memory** - Implement a memory feature, so the agent can remember previous states and actions. 
This solves to problem of the context window being exhausted after a number of loop executions, 
especially if multiple (large) websites area visited.
Idea: Use a vector database to store memories, 
which are either generated explicitly by the agent (expand the response model), 
or use a separate LLM call to summarize one or a batch of interactions.
The generated memories can the be embedded and stored in the database.
Cosine similarity can be used to retrieve memories.
- [ ] **Text editor app** - Implement an app which can edit text files, with a more ergonomic interface for the agent.
Currently, the agent defaults to writing files by `cat`ing each line, which is not token-efficient and leads to mistakes.
A text editor would provide actions to open a specific file on the connected Docker container (also via SSH),
and provide actions to insert, delete, and edit lines of the file.

## Notes
- Obviously, this is not a production-ready system. 
If you stumble upon this repo anyway and find it useful, shoot me a message on X/Twitter.
- The vast majority of the code was written by LLMs (Cursor and to a lesser degree ChatGPT), 
so it's a bit sloppy in places.
I promise I can write cleaner code during the day, but for side projects like this, 
the development speed is more important.