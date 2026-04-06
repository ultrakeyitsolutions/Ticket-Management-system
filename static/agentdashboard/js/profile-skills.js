// Profile Skills & Tags Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const addSkillBtn = document.getElementById('add-skill-btn');
    const newSkillInput = document.getElementById('new-skill-input');
    const skillsList = document.getElementById('skills-list');
    
    // Load existing skills on page load
    loadSkills();
    
    // Add skill button click handler
    if (addSkillBtn) {
        addSkillBtn.addEventListener('click', addSkill);
    }
    
    // Enter key handler for input
    if (newSkillInput) {
        newSkillInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addSkill();
            }
        });
    }
    
    function addSkill() {
        const skillName = newSkillInput.value.trim();
        
        if (!skillName) {
            alert('Please enter a skill or tag name');
            return;
        }
        
        // Get current skills
        const currentSkills = getCurrentSkills();
        
        // Check for duplicates
        if (currentSkills.some(skill => skill.toLowerCase() === skillName.toLowerCase())) {
            alert('This skill already exists');
            return;
        }
        
        // Add new skill
        currentSkills.push(skillName);
        
        // Save to backend
        saveSkills(currentSkills);
    }
    
    function getCurrentSkills() {
        const badges = skillsList.querySelectorAll('.badge');
        const skills = [];
        
        badges.forEach(badge => {
            // Remove the '×' character if present
            const skillText = badge.textContent.replace('×', '').trim();
            if (skillText) {
                skills.push(skillText);
            }
        });
        
        return skills;
    }
    
    function saveSkills(skills) {
        fetch('/dashboard/agent-dashboard/save-skills/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ skills: skills })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear input
                newSkillInput.value = '';
                // Reload skills display
                loadSkills();
            } else {
                alert('Error saving skills: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error saving skills:', error);
            alert('Error saving skills. Please try again.');
        });
    }
    
    function loadSkills() {
        fetch('/dashboard/agent-dashboard/get-skills/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displaySkills(data.skills || []);
            } else {
                console.error('Error loading skills:', data.message);
            }
        })
        .catch(error => {
            console.error('Error loading skills:', error);
        });
    }
    
    function displaySkills(skills) {
        if (!skillsList) return;
        
        skillsList.innerHTML = '';
        
        skills.forEach(skill => {
            const badge = createSkillBadge(skill);
            skillsList.appendChild(badge);
        });
        
        // If no skills, show placeholder
        if (skills.length === 0) {
            skillsList.innerHTML = '<span class="text-muted">No skills added yet</span>';
        }
    }
    
    function createSkillBadge(skillName) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary-subtle text-primary border me-1 mb-1';
        badge.style.cursor = 'pointer';
        badge.innerHTML = `
            ${skillName}
            <span style="margin-left: 5px; font-weight: bold;">×</span>
        `;
        
        // Add click handler to remove skill
        badge.addEventListener('click', function() {
            removeSkill(skillName);
        });
        
        return badge;
    }
    
    function removeSkill(skillName) {
        if (!confirm(`Remove "${skillName}" from your skills?`)) {
            return;
        }
        
        const currentSkills = getCurrentSkills();
        const updatedSkills = currentSkills.filter(skill => skill !== skillName);
        
        saveSkills(updatedSkills);
    }
    
    function getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }
});
