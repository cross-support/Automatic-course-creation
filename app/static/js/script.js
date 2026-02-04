document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('research-form');

    if (!form) return;

    const inputSection = document.getElementById('input-section');
    const resultSection = document.getElementById('result-section');
    const bar = document.getElementById('progress-bar');
    const statusInfo = document.getElementById('status-info');
    const actionArea = document.getElementById('final-action-area');
    const submitBtn = document.getElementById('submit-btn');
    const btnSpinner = document.getElementById('btn-spinner');
    const btnText = document.getElementById('btn-text');
    const retryArea = document.getElementById('retry-area');

    form.onsubmit = async (e) => {
        e.preventDefault();

        setLoadingState(true);
        const formData = new FormData(e.target);

        inputSection.classList.add('hidden');
        resultSection.classList.remove('hidden');

        actionArea.innerHTML = '';
        retryArea.classList.add('hidden');
        updateProgress(0, "サーバー接続を試行中···");

        try {
            const response = await fetch('/api/v1/research/preview', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `サーバーエラー (${response.status})`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;

                    let res;

                    try {
                        res = JSON.parse(line);
                    } catch (parseErr) {
                        console.warn("JSON構文解析飛ばし:", line);
                        continue;
                    }

                    handleStreamResponse(res);
                }
            }

        } catch (err) {
            console.error("Critical Error:", err);
            alert("エラーが発生しました:\n" + err.message);
            inputSection.classList.remove('hidden');
            resultSection.classList.add('hidden');
        } finally {
            setLoadingState(false);
        }
    };

    function setLoadingState(isLoading) {
        submitBtn.disabled = isLoading;
        if (isLoading) {
            btnSpinner.classList.remove('hidden');
            btnText.innerText = "処理中...";
        } else {
            btnSpinner.classList.add('hidden');
            btnText.innerText = "PPT作成開始";
        }
    }

    function updateProgress(percent, message) {
        if (percent !== undefined) {
            bar.style.width = `${percent}%`;
            bar.innerText = `${percent}%`;
        }
        if (message) {
            statusInfo.innerText = message;
        }
    }

    function handleStreamResponse(res) {
        if (res.status === 'progress') {
            updateProgress(res.percent, res.message);
        }
        else if (res.status === 'complete') {
            updateProgress(100, res.message);
            statusInfo.innerHTML = `<span class="text-success fw-bold">${res.message}</span>`;

            if (res.url) {
                renderFinalButton(res.url);
                retryArea.classList.remove('hidden');
            }
        }
        else if (res.status === 'error') {
            throw new Error(res.message);
        }
    }

    function renderFinalButton(url) {
        actionArea.innerHTML = `
            <div class="alert alert-success d-inline-block px-5 py-4 shadow-sm mt-3 animate__animated animate__bounceIn">
                <h4 class="alert-heading fw-bold">🎉 作成完了!</h4>
                <p class="mb-3">下のボタンを押してスライドを確認してください。</p>
                <a href="${url}" target="_blank" class="btn btn-success btn-lg fw-bold px-5 py-3 shadow">
                    📊 Googleスライドを開く
                </a>
            </div>
        `;
    }
});