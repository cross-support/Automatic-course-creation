document.getElementById('research-form').onsubmit = async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const formSide = document.getElementById('form-side');
    const statusSide = document.getElementById('status-side');
    const statusMsg = document.getElementById('status-msg');
    const progressBar = document.getElementById('bar');

    formSide.classList.add('hidden');
    statusSide.classList.remove('hidden');

    try {
        const response = await fetch('/api/v1/research/preview', { 
            method: 'POST', 
            body: formData 
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                const res = JSON.parse(line);

                if (res.status === 'progress') {
                    statusMsg.innerText = res.message;
                    progressBar.style.width = res.percent + '%';
                } 
                else if (res.status === 'complete') {
                    handleDownload(res.data, formData.get('unit_no'));
                }
                else if (res.status === 'error') {
                    alert(res.message);
                    location.reload();
                }
            }
        }
    } catch (err) {
        console.error("데이터 처리 중 오류:", err);
        alert("서버 연결에 실패했습니다.");
        location.reload();
    }
};

function handleDownload(data, unitNo) {
    document.getElementById('status-msg').innerText = "생성 완료!";
    document.getElementById('bar').style.width = '100%';

    const blob = new Blob([JSON.stringify(data, null, 4)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research_result_unit_${unitNo}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    
    document.getElementById('sub-msg').innerText = "파일 다운로드가 시작되었습니다.";
}