document.getElementById('research-form').onsubmit = async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const inputSection = document.getElementById('input-section');
    const resultSection = document.getElementById('result-section');
    const container = document.getElementById('slide-container');
    const bar = document.getElementById('progress-bar');
    const statusInfo = document.getElementById('status-info');

    inputSection.classList.add('hidden');
    resultSection.classList.remove('hidden');

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
                    const s = res.data;
                    const percent = Math.round((res.current / res.total) * 100);
                    
                    bar.style.width = percent + '%';
                    bar.innerText = percent + '%';
                    statusInfo.innerText = `진행 중: ${res.current} / ${res.total} (${s.slide_title})`;

                    appendSlideCard(container, s);
                } 
                else if (res.status === 'error') {
                    alert(res.message);
                    location.reload();
                }
                else if (res.status === 'complete') {
                    statusInfo.innerText = "모든 원고 생성이 완료되었습니다.";
                    bar.classList.remove('progress-bar-animated');
                }
            }
        }
    } catch (err) {
        console.error(err);
        alert("원고 생성 중 오류가 발생했습니다.");
    }
};

function appendSlideCard(container, s) {
    const cardHtml = `
        <div class="slide-card">
            <h3 class="fw-bold">Slide ${s.slide_number}. ${s.slide_title}</h3>
            <hr>
            <div class="row">
                <div class="col-md-6 border-end">
                    <p><strong>[Conclusion]</strong><br>${s.conclusion}</p>
                    <p><strong>[Key Messages]</strong><pre>${s.key_messages.join('\n')}</pre></p>
                </div>
                <div class="col-md-6">
                    <p><strong>[Case Study]</strong><pre>${s.case_study}</pre></p>
                    <p class="text-danger"><strong>[Pitfalls]</strong><br>${s.pitfalls.join(', ')}</p>
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', cardHtml);
    
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}