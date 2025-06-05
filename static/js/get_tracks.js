document.querySelectorAll('.remove_btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const li = this.closest('li');
        const trackId = li.getAttribute('data-track-id');
        fetch('/remove-track', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({track_id: trackId})
        })
        .then(response => response.json())
        .then(data => {
        if (data.success) {
            li.remove();
        } else {
            alert('Failed to remove track, please retry');
        }
        });
    });
    });
  