(async () => {
  const status = document.getElementById('load-status');
  try {
    const response = await fetch('./openapi.json', {
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
      cache: 'no-cache',
    });
    if (!response.ok) throw new Error('schema unavailable');
    const spec = await response.json();
    SwaggerUIBundle({
      spec,
      dom_id: '#swagger-ui',
      deepLinking: true,
      filter: true,
      displayRequestDuration: true,
      defaultModelsExpandDepth: 0,
      docExpansion: 'list',
      syntaxHighlight: { theme: 'nord' },
      supportedSubmitMethods: [],
      tryItOutEnabled: false,
      validatorUrl: null,
      queryConfigEnabled: false,
      persistAuthorization: false,
      withCredentials: false,
    });
    status.hidden = true;
  } catch {
    status.textContent = 'Не удалось загрузить Swagger. Файл OpenAPI доступен по кнопке выше.';
    status.setAttribute('role', 'alert');
  }
})();
