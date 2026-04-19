document.addEventListener('DOMContentLoaded', () => {

    // --- Authentication Logic ---
    const tabLogin = document.getElementById('tabLogin');
    const tabSignup = document.getElementById('tabSignup');
    const formLogin = document.getElementById('loginForm');
    const formSignup = document.getElementById('signupForm');

    if (tabLogin && tabSignup) {
        tabLogin.addEventListener('click', () => {
            tabLogin.classList.add('active');
            tabSignup.classList.remove('active');
            formLogin.classList.add('active');
            formSignup.classList.remove('active');
        });

        tabSignup.addEventListener('click', () => {
            tabSignup.classList.add('active');
            tabLogin.classList.remove('active');
            formSignup.classList.add('active');
            formLogin.classList.remove('active');
        });
    }

    if (formLogin) {
        formLogin.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            const errorDiv = document.getElementById('loginError');

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = '/checker';
                } else {
                    errorDiv.innerText = data.error || "Login failed";
                }
            } catch (err) {
                errorDiv.innerText = "Network error. Try again.";
            }
        });
    }

    if (formSignup) {
        formSignup.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('signupError');
            
            const payload = {
                name: document.getElementById('signupName').value,
                email: document.getElementById('signupEmail').value,
                password: document.getElementById('signupPassword').value,
                age: document.getElementById('signupAge').value,
                gender: document.getElementById('signupGender').value,
                dosha: document.getElementById('signupDosha').value,
                district: document.getElementById('signupDistrict').value
            };

            try {
                const res = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = '/checker';
                } else {
                    errorDiv.innerText = data.error || "Signup failed";
                }
            } catch (err) {
                errorDiv.innerText = "Network error. Try again.";
            }
        });
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/';
        });
    }

    // --- Symptom Checker Logic ---
    const searchInput = document.getElementById('symptomSearch');
    const symptomsList = document.getElementById('symptomsList');
    const selectedTags = document.getElementById('selectedTags');
    const analyzeBtn = document.getElementById('analyzeBtn');
    let selectedSymptoms = [];

    if (searchInput && symptomsList) {
        const labels = symptomsList.querySelectorAll('.symptom-item');
        
        searchInput.addEventListener('input', (e) => {
            const val = e.target.value.toLowerCase();
            labels.forEach(label => {
                const text = label.querySelector('.symptom-name').innerText.toLowerCase();
                if (text.includes(val)) {
                    label.style.display = 'flex';
                } else {
                    label.style.display = 'none';
                }
            });
        });

        labels.forEach(label => {
            const checkbox = label.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', () => {
                const symptomRaw = checkbox.value;
                const symptomName = label.querySelector('.symptom-name').innerText;
                
                if (checkbox.checked) {
                    if (!selectedSymptoms.includes(symptomRaw)) {
                        selectedSymptoms.push(symptomRaw);
                        addTag(symptomRaw, symptomName, checkbox);
                    }
                } else {
                    selectedSymptoms = selectedSymptoms.filter(s => s !== symptomRaw);
                    removeTagDOM(symptomRaw);
                }
                updateAnalyzeBtn();
            });
        });
    }

    function addTag(raw, name, checkbox) {
        const tag = document.createElement('div');
        tag.className = 'symptom-tag';
        tag.id = `tag-${raw}`;
        tag.innerHTML = `
            ${name} 
            <span class="remove-tag" data-raw="${raw}">&times;</span>
        `;
        selectedTags.appendChild(tag);

        tag.querySelector('.remove-tag').addEventListener('click', (e) => {
            const r = e.target.getAttribute('data-raw');
            selectedSymptoms = selectedSymptoms.filter(s => s !== r);
            checkbox.checked = false;
            removeTagDOM(r);
            updateAnalyzeBtn();
        });
    }

    function removeTagDOM(raw) {
        const tag = document.getElementById(`tag-${raw}`);
        if (tag) tag.remove();
    }

    function updateAnalyzeBtn() {
        const errorDiv = document.getElementById('analyzeError');
        if (selectedSymptoms.length >= 3) {
            analyzeBtn.disabled = false;
            errorDiv.innerText = '';
        } else if (selectedSymptoms.length > 0) {
            analyzeBtn.disabled = true;
            errorDiv.innerText = 'Please select at least 3 symptoms for a more accurate prediction.';
        } else {
            analyzeBtn.disabled = true;
            errorDiv.innerText = '';
        }
    }

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async () => {
            const errorDiv = document.getElementById('analyzeError');
            analyzeBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing...';
            analyzeBtn.disabled = true;
            errorDiv.innerText = '';

            try {
                const res = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symptoms: selectedSymptoms })
                });
                const data = await res.json();

                if (res.ok) {
                    // Store result in sessionStorage and redirect
                    sessionStorage.setItem('ayurResult', JSON.stringify(data));
                    window.location.href = '/results';
                } else {
                    errorDiv.innerText = data.error || "An error occurred during analysis.";
                    analyzeBtn.innerHTML = 'Analyze Symptoms <i class="fa-solid fa-microscope"></i>';
                    analyzeBtn.disabled = false;
                }
            } catch (err) {
                errorDiv.innerText = "Network error. Is the server running?";
                analyzeBtn.innerHTML = 'Analyze Symptoms <i class="fa-solid fa-microscope"></i>';
                analyzeBtn.disabled = false;
            }
        });
    }

    // --- Results Page Logic ---
    const resultsContainer = document.querySelector('.results-container');
    if (resultsContainer && window.location.pathname === '/results') {
        const resultDataStr = sessionStorage.getItem('ayurResult');
        const loading = document.getElementById('loadingResults');
        const content = document.getElementById('resultsContent');

        if (!resultDataStr) {
            window.location.href = '/checker';
            return;
        }

        const data = JSON.parse(resultDataStr);
        
        setTimeout(() => {
            loading.classList.add('hidden');
            content.classList.remove('hidden');

            document.getElementById('resDisease').innerText = data.disease;

            if (data.is_severe) {
                document.getElementById('severeResult').classList.remove('hidden');
                document.getElementById('resSevereMsg').innerText = data.message;
                
                const docsList = document.getElementById('doctorsList');
                if (data.doctors && data.doctors.length > 0) {
                    docsList.innerHTML = data.doctors.map(d => `
                        <div class="doctor-item">
                            <h4><i class="fa-solid fa-stethoscope"></i> ${d.name}</h4>
                            <div class="sub-text"><i class="fa-solid fa-location-dot"></i> ${d.address}</div>
                            <div class="sub-text mt-10"><i class="fa-solid fa-phone"></i> ${d.contact}</div>
                        </div>
                    `).join('');
                } else {
                    docsList.innerHTML = '<p class="sub-text">No nearby doctors available in your district.</p>';
                }
            } else {
                document.getElementById('normalResult').classList.remove('hidden');
                document.getElementById('resRemedy').innerText = data.remedy;
                document.getElementById('resMedicines').innerText = data.medicines;
                document.getElementById('resReasoning').innerText = data.reasoning;
                document.getElementById('resPreventive').innerText = data.preventive_advice;
            }

            gsap.from(".result-card", { duration: 0.8, y: 30, opacity: 0, stagger: 0.2, ease: "power2.out" });

        }, 1000); // Fake small delay for the spinner animation
    }
});
