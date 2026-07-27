document.addEventListener('DOMContentLoaded', function () {
  const forms = document.querySelectorAll('form[name="subscribe"]');
  forms.forEach(function (form) {
    // create message container
    const msg = document.createElement('div');
    msg.className = 'subscribe-message';
    form.appendChild(msg);

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.textContent = 'Sender...';
      const fd = new FormData(form);
      // Netlify expects form-name in payload; FormData includes it
      const body = new URLSearchParams();
      for (const pair of fd.entries()) body.append(pair[0], pair[1]);

      // Build absolute URL for the form action to avoid issues with base paths
      const targetUrl = new URL(form.getAttribute('action') || '/', window.location.href).toString();
      console.debug('Submitting subscribe form to', targetUrl, 'payload:', body.toString());

      fetch(targetUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
        redirect: 'follow',
      })
        .then(function (res) {
          console.debug('Subscribe response', res.status, res.statusText);
          // Accept 2xx and 3xx as success (Netlify may redirect)
          if (res.status >= 200 && res.status < 400) {
            msg.textContent = 'Takk — du er påmeldt!';
            form.reset();
          } else {
            msg.textContent = 'Kunne ikke sende. Prøv igjen.';
          }
        })
        .catch(function (err) {
          console.error('Subscribe fetch error', err);
          msg.textContent = 'Nettverksfeil. Prøv igjen.';
        });
    });
  });
});
