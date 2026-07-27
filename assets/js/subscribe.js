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
        // Honeypot anti-spam: if filled, treat as success but don't send
        const honeypot = fd.get('website');
        if (honeypot && honeypot.trim() !== '') {
          msg.textContent = 'Takk!';
          form.reset();
          return;
        }
      // Netlify expects form-name in payload; FormData includes it
      const body = new URLSearchParams();
      for (const pair of fd.entries()) body.append(pair[0], pair[1]);

      fetch(form.action || '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      })
        .then(function (res) {
          if (res.ok) {
            msg.textContent = 'Takk — du er påmeldt!';
            form.reset();
          } else {
            msg.textContent = 'Kunne ikke sende. Prøv igjen.';
          }
        })
        .catch(function () {
          msg.textContent = 'Nettverksfeil. Prøv igjen.';
        });
    });
  });
});
