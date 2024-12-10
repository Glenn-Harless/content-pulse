document.addEventListener('DOMContentLoaded', () => {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const queryBtn = document.getElementById('queryBtn');
    const articlesContainer = document.getElementById('articles');
    const queryInput = document.getElementById('queryInput');
    const queryResult = document.getElementById('queryResult');

    // Setup WebSocket connection
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onmessage = function(event) {
        const update = JSON.parse(event.data);
        updateArticleSummary(update.articleId, update.summary);
    };

    // Load articles on page load
    fetchArticles();

    scrapeBtn.addEventListener('click', async () => {
        setLoading(scrapeBtn, true);
        try {
            console.log('Starting scrape request...');
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Scrape response:', data);
            await fetchArticles();
        } catch (error) {
            console.error('Error scraping articles:', error);
            alert('Error scraping articles. Please try again.');
        } finally {
            setLoading(scrapeBtn, false);
        }
    });

    queryBtn.addEventListener('click', async () => {
        const question = queryInput.value.trim();
        if (!question) return;

        setLoading(queryBtn, true);
        try {
            console.log('Sending query:', question);
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ question })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            queryResult.textContent = data.response;
        } catch (error) {
            console.error('Error querying articles:', error);
            alert('Error querying articles. Please try again.');
        } finally {
            setLoading(queryBtn, false);
        }
    });

    async function fetchArticles() {
        try {
            console.log('Fetching articles...');
            const response = await fetch('/articles', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const articles = await response.json();
            console.log('Fetched articles:', articles);
            displayArticles(articles);
        } catch (error) {
            console.error('Error fetching articles:', error);
            articlesContainer.innerHTML = '<div class="alert alert-danger">Error loading articles</div>';
        }
    }

    function displayArticles(articles) {
        articlesContainer.innerHTML = articles.length ? '' : 
            '<div class="alert alert-info">No articles available. Click "Scrape Latest Articles" to fetch some!</div>';
        
        articles.forEach(article => {
            const articleElement = document.createElement('div');
            articleElement.className = 'card article-card';
            articleElement.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">${escapeHtml(article.title)}</h5>
                    <p class="timestamp">Scraped: ${new Date(article.scraped_at).toLocaleString()}</p>
                    <div class="summary-section" id="summary-${article.id}">
                        ${article.summary ? 
                            `<p class="article-summary">${escapeHtml(article.summary)}</p>` :
                            `<div class="summary-loading">
                                <div class="d-flex align-items-center">
                                    <div class="spinner-border spinner-border-sm me-2"></div>
                                    <span>Generating summary...</span>
                                </div>
                                <div class="progress-bar-container mt-2">
                                    <div class="progress-bar" style="width: 0%"></div>
                                </div>
                            </div>`
                        }
                    </div>
                    <div class="mt-3">
                        <a href="${article.url}" target="_blank" class="btn btn-outline-primary btn-sm me-2">Read Full Article</a>
                        ${!article.summary ? 
                            `<button class="btn btn-outline-secondary btn-sm generate-summary" data-article-id="${article.id}">
                                Generate Summary
                            </button>` : ''
                        }
                    </div>
                </div>
            `;
            articlesContainer.appendChild(articleElement);

            // Add event listener for generate summary button if it exists
            const generateBtn = articleElement.querySelector('.generate-summary');
            if (generateBtn) {
                generateBtn.addEventListener('click', () => generateSummary(article.id));
            }
        });
    }

    async function generateSummary(articleId) {
        try {
            const response = await fetch(`/generate-summary/${articleId}`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Summary generation started - UI will update via WebSocket
            const summarySection = document.getElementById(`summary-${articleId}`);
            summarySection.innerHTML = `
                <div class="summary-loading">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2"></div>
                        <span>Generating summary...</span>
                    </div>
                    <div class="progress-bar-container mt-2">
                        <div class="progress-bar" style="width: 0%"></div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error generating summary:', error);
            alert('Error generating summary. Please try again.');
        }
    }

    function updateArticleSummary(articleId, summary, progress = 100) {
        const summarySection = document.getElementById(`summary-${articleId}`);
        if (!summarySection) return;

        if (progress < 100) {
            // Update progress bar
            const progressBar = summarySection.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
        } else {
            // Summary is complete
            summarySection.innerHTML = `<p class="article-summary">${escapeHtml(summary)}</p>`;
            
            // Remove the generate summary button if it exists
            const generateBtn = document.querySelector(`button[data-article-id="${articleId}"]`);
            if (generateBtn) {
                generateBtn.remove();
            }
        }
    }

    function setLoading(button, isLoading) {
        const spinner = button.querySelector('.spinner-border');
        spinner.classList.toggle('d-none', !isLoading);
        button.disabled = isLoading;
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});