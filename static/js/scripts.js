let editors = [];

let recordingActive = false;
let ttsActive = false;


function toggleMic() {
    recordingActive = !recordingActive;
    const micButton = document.getElementById('mic-button');
    const micIndicator = document.getElementById('mic-indicator');

    if (recordingActive) {
        micButton.classList.remove('btn-secondary');
        micButton.classList.add('btn-danger');
        micIndicator.classList.remove('led-red');
        micIndicator.classList.add('led-green');
        startRecording();
    } else {
        micButton.classList.remove('btn-danger');
        micButton.classList.add('btn-secondary');
        micIndicator.classList.remove('led-green');
        micIndicator.classList.add('led-red');
        stopRecording();
    }
}

function toggleTTS() {
    ttsActive = !ttsActive;
    const ttsButton = document.getElementById('tts-button');
    const ttsIndicator = document.getElementById('tts-indicator');

    if (ttsActive) {
        ttsButton.classList.remove('btn-secondary');
        ttsButton.classList.add('btn-danger');
        ttsIndicator.classList.remove('led-red');
        ttsIndicator.classList.add('led-green');
    } else {
        ttsButton.classList.remove('btn-danger');
        ttsButton.classList.add('btn-secondary');
        ttsIndicator.classList.remove('led-green');
        ttsIndicator.classList.add('led-red');
    }
}


function startRecording() {
    fetch('/start_recording', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.status);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function stopRecording() {
    fetch('/stop_recording', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.status);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    checkHealth();
    setInterval(checkHealth, 400000); // 30초마다 checkHealth 호출
    loadChatHistory();
    loadPrompt();
    loadFunctions();
    loadEmotionPrompt();

    // Input 텍스트 박스에서 엔터 키를 눌렀을 때 sendMessage 호출
    document.getElementById('input-text').addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // 기본 엔터 키 동작 방지
            sendMessage();
        }
    });
});

function loadEmotionPrompt() {
    fetch('/get_emotion_prompt')
        .then(response => response.json())
        .then(data => {
            document.getElementById('emotion-prompt').value = data.prompt;
            const emotionTableBody = document.getElementById('emotion-table').querySelector('tbody');
            emotionTableBody.innerHTML = '';
            data.emotions.forEach((emotion, index) => {
                addEmotionRow(emotion.emotion, emotion.description, index);
            });
        });
}

function addEmotion() {
    const emotionTableBody = document.getElementById('emotion-table').querySelector('tbody');
    addEmotionRow('', '', emotionTableBody.rows.length);
}

function addEmotionRow(emotion = '', description = '', index) {
    const emotionTableBody = document.getElementById('emotion-table').querySelector('tbody');
    const row = emotionTableBody.insertRow(index);

    const cell1 = row.insertCell(0);
    const emotionInput = document.createElement('input');
    emotionInput.type = 'text';
    emotionInput.className = 'form-control';
    emotionInput.value = emotion;
    cell1.appendChild(emotionInput);

    const cell2 = row.insertCell(1);
    const descriptionInput = document.createElement('input');
    descriptionInput.type = 'text';
    descriptionInput.className = 'form-control';
    descriptionInput.value = description;
    cell2.appendChild(descriptionInput);

    const cell3 = row.insertCell(2);
    const deleteButton = document.createElement('button');
    deleteButton.className = 'btn btn-danger';
    deleteButton.innerText = 'Delete';
    deleteButton.onclick = () => {
        row.remove();
    };
    cell3.appendChild(deleteButton);
}

function saveEmotionPrompt() {
    const prompt = document.getElementById('emotion-prompt').value;
    const emotionTableBody = document.getElementById('emotion-table').querySelector('tbody');
    const emotions = [];

    for (let i = 0; i < emotionTableBody.rows.length; i++) {
        const row = emotionTableBody.rows[i];
        const emotion = row.cells[0].querySelector('input').value;
        const description = row.cells[1].querySelector('input').value;
        emotions.push(`{"${emotion}" 이 감정에 대한 예시 : "${description}"}`);
    }

    const data = `${prompt}\nEmotion List:\n${emotions.join(',\n')}`;

    fetch('/save_emotion_prompt', {
        method: 'POST',
        headers: {
            'Content-Type': 'text/plain',
        },
        body: data,
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Emotion prompt saved successfully!');
        }
    });
}

function checkHealth() {
    fetch('/health')
        .then(response => response.json())
        .then(data => {
            const healthIndicator = document.getElementById('health-indicator');
            const healthText = document.getElementById('health-text');
            if (data.status === 'healthy') {
                healthIndicator.classList.add('led-green');
                healthIndicator.classList.remove('led-red');
                healthText.innerText = '서버가 정상 작동하고 있습니다!';
            } else {
                healthIndicator.classList.add('led-red');
                healthIndicator.classList.remove('led-green');
                healthText.innerText = '서버에 문제가 발생했습니다!';
            }
        })
        .catch(error => {
            const healthIndicator = document.getElementById('health-indicator');
            const healthText = document.getElementById('health-text');
            healthIndicator.classList.add('led-red');
            healthIndicator.classList.remove('led-green');
            healthText.innerText = '서버에 문제가 발생했습니다!';
        });
}

function sendMessage() {
    const inputText = document.getElementById('input-text').value;
    const outputText = document.getElementById('output-text');

    if (ttsActive == true) {
        fetch('http://localhost:6006/proxy/callGPTChatWithTTS', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ say: inputText }),
            mode: 'cors'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            console.log("Blob URL:", url);
            const audio = new Audio(url);
            audio.play();
        })
        .catch(error => console.error('Error:', error));
    } else {
        fetch('http://localhost:6006/proxy/callGPTChat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ say: inputText }),
            mode: 'cors'  // CORS 모드 추가
        })
        .then(response => response.json())
        .then(data => {
            outputText.value = data.say;
            document.getElementById('input-text').value = ''; // 입력 필드 비우기
        })
        .catch(error => console.error('Error:', error));
    }
}

function loadChatHistory() {
    fetch('/get_chat_history')
        .then(response => response.json())
        .then(data => {
            const chatHistoryContainer = document.getElementById('chat-history-container');
            chatHistoryContainer.innerHTML = '';
            data.chat_history.forEach((entry, index) => {
                addChatBlock(entry, index);
            });
        })
        .catch(error => console.error('Error loading chat history:', error));
}

function addChatBlock(entry, index) {
    const chatHistoryContainer = document.getElementById('chat-history-container');
    const block = document.createElement('div');
    block.className = 'chat-block mt-3 p-3 border rounded';
    block.setAttribute('data-index', index);

    const userText = document.createElement('p');
    userText.innerText = `User: ${entry.user}`;

    const aiText = document.createElement('p');
    aiText.innerText = `AI: ${entry.ai}`;

    const positiveButton = document.createElement('button');
    positiveButton.className = 'btn mt-2 mr-2';
    positiveButton.innerText = '👍';
    positiveButton.style.backgroundColor = entry.positive === true ? '#28a745' : '#6c757d'; // green if positive, gray otherwise
    positiveButton.onclick = () => {
        updateChatHistory(entry, true);
        positiveButton.style.backgroundColor = '#28a745'; // green
        negativeButton.style.backgroundColor = '#6c757d'; // gray
    };

    const negativeButton = document.createElement('button');
    negativeButton.className = 'btn mt-2';
    negativeButton.innerText = '👎';
    negativeButton.style.backgroundColor = entry.positive === false ? '#dc3545' : '#6c757d'; // red if negative, gray otherwise
    negativeButton.onclick = () => {
        updateChatHistory(entry, false);
        positiveButton.style.backgroundColor = '#6c757d'; // gray
        negativeButton.style.backgroundColor = '#dc3545'; // red
    };

    block.appendChild(userText);
    block.appendChild(aiText);
    block.appendChild(positiveButton);
    block.appendChild(negativeButton);

    chatHistoryContainer.appendChild(block);
}

function updateChatHistory(entry, positive) {
    entry.positive = positive;
    fetch('/update_chat_history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Chat history updated successfully!');
        }
    });
}

function loadPrompt() {
    fetch('/get_prompt')
        .then(response => response.json())
        .then(data => {
            document.getElementById('system-prompt').value = data.system;
            document.getElementById('character-prompt').value = data.character;
            document.getElementById('command-prompt').value = data.command;
        });
}

function savePrompt() {
    const system = document.getElementById('system-prompt').value;
    const character = document.getElementById('character-prompt').value;
    const command = document.getElementById('command-prompt').value;
    fetch('/save_prompt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ system, character, command }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Prompt saved successfully!');
        }
    });
}

function loadFunctions() {
    fetch('/get_functions')
        .then(response => response.json())
        .then(data => {
            const functionsContainer = document.getElementById('functions-container');
            functionsContainer.innerHTML = '';
            editors = [];
            data.functions.forEach((func, index) => {
                addFunctionBlock(func, index);
            });
        })
        .catch(error => console.error('Error loading functions:', error));
}

function addFunctionBlock(func = {name: '', description: '', parameter: '', content: ''}, index = editors.length) {
    const functionsContainer = document.getElementById('functions-container');
    const block = document.createElement('div');
    block.className = 'function-block mt-3 p-3 border rounded collapsed';
    block.setAttribute('data-index', index);

    const headerDiv = document.createElement('div');
    headerDiv.className = 'function-header d-flex align-items-center';
    headerDiv.onclick = () => block.classList.toggle('collapsed');

    const nameLabel = document.createElement('label');
    nameLabel.innerText = 'Function Name:';
    nameLabel.className = 'mr-2';
    const nameInput = document.createElement('input');
    nameInput.className = 'form-control d-inline-block w-25';
    nameInput.placeholder = 'Function Name';
    nameInput.value = func.name || '';

    const descriptionLabel = document.createElement('label');
    descriptionLabel.innerText = 'Function Description:';
    descriptionLabel.className = 'ml-3 mr-2';
    const descriptionInput = document.createElement('input');
    descriptionInput.className = 'form-control d-inline-block w-50';
    descriptionInput.placeholder = 'Function Description';
    descriptionInput.value = func.description || '';

    headerDiv.appendChild(nameLabel);
    headerDiv.appendChild(nameInput);
    headerDiv.appendChild(descriptionLabel);
    headerDiv.appendChild(descriptionInput);

    const detailsDiv = document.createElement('div');
    detailsDiv.className = 'function-details';

    const paramsLabel = document.createElement('label');
    paramsLabel.innerText = 'Function Parameters:';
    const paramsInput = document.createElement('textarea');
    paramsInput.className = 'form-control function-params';
    paramsInput.rows = 3;
    paramsInput.placeholder = 'param1, param2, ...';
    paramsInput.value = func.parameter || '';

    const contentLabel = document.createElement('label');
    contentLabel.innerText = 'Function Content:';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'monaco-editor-container';

    const deleteButton = document.createElement('button');
    deleteButton.className = 'btn btn-danger mt-2';
    deleteButton.innerText = 'Delete';
    deleteButton.onclick = () => {
        const functionName = nameInput.value; // 함수 이름을 사용하여 삭제 요청
        fetch(`/delete_function/${encodeURIComponent(functionName)}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                block.remove();
            } else {
                console.error('Error deleting function.');
            }
        });
    };

    detailsDiv.appendChild(paramsLabel);
    detailsDiv.appendChild(paramsInput);
    detailsDiv.appendChild(contentLabel);
    detailsDiv.appendChild(contentDiv);
    detailsDiv.appendChild(deleteButton);

    block.appendChild(headerDiv);
    block.appendChild(detailsDiv);

    functionsContainer.appendChild(block);

    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.33.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {
        const editor = monaco.editor.create(contentDiv, {
            value: func.content || '',
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true
        });

        editors.push({ nameInput, descriptionInput, editor, paramsInput });
    });
}

function saveFunctions() {
    const functions = editors.map(editor => {
        const name = editor.nameInput.value;
        const description = editor.descriptionInput.value;
        const parameter = editor.paramsInput.value;
        const content = editor.editor.getValue();
        return { name, description, content, parameter};
    });
    fetch('/save_functions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ functions: functions }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Functions saved successfully!');
        }
    });
}

function addFunction() {
    addFunctionBlock();
}

function restartServer() {
    fetch('/restart_server', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'restarting') {
            alert('Server is restarting...');
        }
    });
}