// Simple Vercel Serverless function that returns an HTML page embedding
// the Streamlit dashboard via an iframe. Set STREAMLIT_URL in Vercel env.

module.exports = (req, res) => {
  const streamlitUrl = process.env.STREAMLIT_URL || 'https://your-streamlit-url.example';
  const html = `<!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Review Opportunity Dashboard</title>
      <style>html,body,iframe{height:100%;margin:0;padding:0}iframe{width:100%;border:none}</style>
    </head>
    <body>
      <iframe src="${streamlitUrl}" title="Dashboard" sandbox="allow-forms allow-scripts allow-same-origin allow-popups"></iframe>
    </body>
  </html>`;
  res.setHeader('Content-Type', 'text/html');
  res.statusCode = 200;
  res.end(html);
};
