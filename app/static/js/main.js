/**
 * ReFind AI - Frontend Interactions & Dynamic Behaviors
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Automatic Image Preview Handler
    const imageInput = document.querySelector('input[type="file"][name="image"]');
    const previewContainer = document.getElementById('image-preview-container');
    const previewImg = document.getElementById('image-preview-img');
    const dropzonePlaceholder = document.getElementById('dropzone-placeholder');

    if (imageInput && previewContainer && previewImg) {
        imageInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewImg.src = e.target.result;
                    previewContainer.classList.remove('d-none');
                    if (dropzonePlaceholder) {
                        dropzonePlaceholder.classList.add('d-none');
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 2. Auto-dismiss Bootstrap Alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach((alert) => {
        setTimeout(() => {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {
                // Alert might already be closed by user
            }
        }, 6000);
    });

    // 3. Mark Notification Read via Fetch API
    const notifButtons = document.querySelectorAll('.btn-mark-notif-read');
    notifButtons.forEach((btn) => {
        btn.addEventListener('click', async function (e) {
            e.preventDefault();
            const notifId = this.getAttribute('data-notif-id');
            const row = document.getElementById(`notif-row-${notifId}`);
            try {
                const resp = await fetch(`/notification/${notifId}/read`, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                if (resp.ok) {
                    if (row) {
                        row.classList.remove('bg-light');
                        row.classList.add('opacity-75');
                    }
                    this.remove();
                }
            } catch (err) {
                console.error('Failed to mark notification as read:', err);
            }
        });
    });

    // 4. Copy to Clipboard Utility
    window.copyToClipboard = function (text, buttonElement) {
        navigator.clipboard.writeText(text).then(() => {
            const originalHtml = buttonElement.innerHTML;
            buttonElement.innerHTML = '<i class="bi bi-check-lg text-success"></i> Copied!';
            setTimeout(() => {
                buttonElement.innerHTML = originalHtml;
            }, 2000);
        }).catch(err => {
            console.error('Copy failed:', err);
        });
    };
});
