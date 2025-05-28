async function createPlaylist() {
    const spinner = document.getElementById('spinner');
    const status = document.getElementById('status');
    const playlistInput = document.getElementById('playlist-id');
    status.textContent = '';
    playlistInput.style.display = 'none';
    spinner.style.display = 'inline-block';

    try {
        const response = await fetch('/init-archive', { method: 'POST' });
        spinner.style.display = 'none';

        if (!response.ok) {
            const errData = await response.json();
            status.innerHTML = `<span class="error">❌ Error: ${errData.message || response.statusText}</span>`;
            return;
        }

        const data = await response.json();
        playlistInput.value = data.playlist_id;
        playlistInput.style.display = 'block';

        // Copy to clipboard
        await navigator.clipboard.writeText(data.playlist_id);

        status.innerHTML = `
            <span class="success">✅ Playlist created and ID copied to clipboard!</span><br>
            <strong>Playlist ID:</strong> ${data.playlist_id}
        `;
    } catch (error) {
        spinner.style.display = 'none';
        status.innerHTML = `<span class="error">❌ Error: ${error.message}</span>`;
    }
}