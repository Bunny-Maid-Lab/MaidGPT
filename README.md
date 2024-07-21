
# Home Maid Project (MaidGPT)

MaidGPT is a project that implements a maid (or any desired character) using GPT, providing a management page and various utilities to easily use IoT and related features. Here are the main features of MaidGPT:

## MaidGPT Management Page 🛠️

The MaidGPT management page is designed to easily manage the main features of MaidGPT.

### 1. Main Test Webpage
- **Character Main Image**
- **Server Status and Log Check**
- **Chat and Microphone Input Test**

### 2. Chat History Management and Human Feedback
- **View Chat History**
- **Evaluate Chat History**

### 3. Prompt Management
- **System Prompt**
- **Character Prompt**
- **Function Prompt**

### 4. Emotion Output Management
- **Emotion Classification Prompt**
- **Compose List of Emotions and Examples**

### 5. Python Function Management
- **Manage, Delete, Save Function List**
- **Function Coding**

We plan to continuously improve usability and add various features.

## MaidGPT Messenger 📲

Originally, MaidGPT was designed to receive emotion data and make various movements in Unity3D, but due to the inclusion of non-distributable VRChat model-related libraries, it could not be distributed. Instead, we created a simple chat program in Python to easily use MaidGPT's features.

[Home Maid Messenger](https://www.notion.so/2cee834d66b04df4a374d686432c51f1?pvs=21)

The MaidGPT web management page allows you to execute various functions.

The management page is divided into a web page and a server that organizes results after MaidGPT actually communicates with GPT and executes functions.

\`\`\`bash
python app.py
\`\`\`

With the above command, you can start the MaidGPT web server, MaidGPT server, and STT and TTS servers all at once.

## MaidGPT Web Page Manual 📘

![Main Page](Assets/Untitled.png)

First, the login feature prevents unauthorized access to the management page from outside.

You can set the username and password in \`server_config.json\`.

### Username/Password Setup

![Setup](Assets/Untitled%201.png)

On the main page, you can see the character's image and the server's health check status to ensure the server is operating normally. Below, there are chat and mic buttons to test chat and voice recognition.

The mic button records audio while pressed, sends the audio to OpenAI Whisper for Speech-to-Text after a second of silence, and automatically sends the resulting message.

![Chat](Assets/Untitled%202.png)

In the Chat History menu, you can view and evaluate past chats with likes and dislikes for future data use. Evaluated chat history is saved in \`chat_history.json\`.

![Edit Prompt](Assets/Untitled%203.png)

In the Edit Prompt menu, you can set prompts. You can write system prompts for basic conversation quality, character-specific prompts, and function-calling prompts.

Function-calling prompts help execute specific commands and pass parameters.

![Edit Functions](Assets/Untitled%204.png)

In the Edit Functions screen, you can add or delete desired functions.

By adding desired functions, users can customize the maid to perform various tasks using different APIs.

After writing all functions, save them with the Save All button and restart the server with the Restart Server button to apply the functions.

The repository includes example functions using Samsung SmartThings and LG Thinq. For LG Thinq, we used [this repository](https://github.com/majki09/domoticz_lg_thinq_plugin).

### Function Writing Rules and Principles
- When using external modules, write the import statement inside the function like this:

\`\`\`python
def set_acTemp(temp):
    from LGPlugin import client as LGClient
    thinqClient = LGClient.client_set()
    temp = int(temp)
    if 17 < temp < 28:
        LGClient.set_temp(thinqClient, "AC_DEVICE_CODE", temp)
        return True
    else:
        return False
\`\`\`

- Each function must have a return statement. For success/failure, use \`return True\` / \`return False\`. For returning specific values, set the return value like this:

\`\`\`python
def timeKST():
    from datetime import datetime, timedelta, timezone
    utc_now = datetime.utcnow()
    kst_timezone = timezone(timedelta(hours=9))
    kst_now = utc_now.replace(tzinfo=timezone.utc).astimezone(kst_timezone)
    return kst_now.strftime('%Y-%m-%d %H:%M:%S %Z%z')
\`\`\`

- Functions are executed internally using \`exec\`. When input is given, the Function Calling receives parameters and finds the function, then the result is stored in a variable using \`result = function_name\`. The result is combined with the character's dialogue and sent back to GPT, which then returns a response.

![Emotion Embedding](Assets/Untitled%205.png)
![Emotion Embedding](Assets/Untitled%206.png)

Finally, each time the maid responds, an emotion classification function is executed to determine the emotion in the response. In the Emotion Embedding tab, you can set how to classify emotions using prompts and define emotions and their triggers in a table.

Save settings with the Save button and apply them by restarting the server with the Restart Server button.

![API Keys](Assets/Untitled%207.png)

API keys for OpenAI and other necessary keys should be set in \`server_config.json\` or within the server code.

## STT/TTS 🎙️
- **STT**: Uses OpenAI's Whisper model, providing both API and local model STT server code. Use the **ip:6008/api/stt** API for STT.
- **TTS**: Uses [MeloTTS](https://github.com/myshell-ai/MeloTTS/), and we wrote \`tts_server.py\` to use the **ip:6007/api/tts** API for local TTS.

For TTS model creation, refer to the MeloTTS repository.

---

This markdown document has been translated into English accurately and styled with emojis and formatting for easy reading.
