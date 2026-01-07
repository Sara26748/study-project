
function sendHeartbeat() {
    fetch(`/project/${window.PROJECT_ID}/heartbeat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    }).catch(err => console.error('Heartbeat error:', err));
}

function pollActiveUsers() {
    fetch(`/project/${window.PROJECT_ID}/active_users`)
        .then(response => response.json())
        .then(users => {
            updateActiveUsersDisplay(users);
        })
        .catch(err => console.error('Active users polling error:', err));
}

function updateActiveUsersDisplay(users) {
    const container = document.getElementById('activeUsersContainer');
    if (!container) return;
    
    if (users.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    // Create avatar badges for active users
    let html = '<div class="d-flex align-items-center gap-1">';
    html += '<span class="text-muted small me-2"><i class="bi bi-circle-fill text-success" style="font-size: 0.5rem;"></i> Aktiv:</span>';
    
    users.forEach(user => {
        const initials = user.initials || user.email.substring(0, 2).toUpperCase();
        const color = stringToColor(user.email);
        
        html += `
            <div class="position-relative" title="${user.email}">
                <div class="rounded-circle d-flex align-items-center justify-content-center text-white fw-bold shadow-sm" 
                     style="width: 32px; height: 32px; background-color: ${color}; font-size: 0.75rem;">
                    ${initials}
                </div>
                <span class="position-absolute bottom-0 end-0 bg-success border border-2 border-white rounded-circle" 
                      style="width: 10px; height: 10px;"></span>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Generate consistent color from string (for user avatars)
function stringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const hue = hash % 360;
    return `hsl(${hue}, 65%, 50%)`;
}
