document.addEventListener('DOMContentLoaded', () => {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const queryBtn = document.getElementById('queryBtn');
    const articlesContainer = document.getElementById('articles');
    const queryInput = document.getElementById('queryInput');
    const queryResult = document.getElementById('queryResult');

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
        articlesContainer.innerHTML = articles.length ? '' : '<div class="alert alert-info">No articles available. Click "Scrape Latest Articles" to fetch some!</div>';
        
        articles.forEach(article => {
            const articleElement = document.createElement('div');
            articleElement.className = 'card article-card';
            articleElement.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">${escapeHtml(article.title)}</h5>
                    <p class="timestamp">Scraped: ${new Date(article.scraped_at).toLocaleString()}</p>
                    <p class="article-summary">${escapeHtml(article.summary || 'No summary available')}</p>
                    <a href="${article.url}" target="_blank" class="btn btn-outline-primary btn-sm">Read Full Article</a>
                </div>
            `;
            articlesContainer.appendChild(articleElement);
        });
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
