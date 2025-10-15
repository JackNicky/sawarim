// Self-executing async function to load external library and then run the worker logic
(async function() {
    try {
        // Fetch the FlexSearch library from the CDN
        const response = await fetch("https://cdn.jsdelivr.net/gh/nextapps-de/flexsearch@0.7.31/dist/flexsearch.bundle.js");
        if (!response.ok) {
            throw new Error('Network response was not ok for FlexSearch library.');
        }
        const scriptText = await response.text();
        // Evaluate the script in the worker's scope
        self.eval(scriptText);
        // Now that FlexSearch is loaded, we can run the main worker logic.
        main();
    } catch (error) {
        console.error('Failed to load FlexSearch library:', error);
        self.postMessage({ type: 'error', payload: { message: 'Failed to load search library.' } });
    }
})();

function main() {
    // All the original worker code will go here.

    // Initialize FlexSearch Document Index
    const index = new FlexSearch.Document({
        charset: 'utf-8',
        lang: 'ar',
        tokenize: 'forward',
        cache: 100,
        document: {
            id: 'id',
            index: ['bookTitle', 'chapter', 'text'],
            store: true, 
        },
    });

    let searchableContent = [];

    // Normalize Arabic text for better matching
    function normalizeText(text) {
        if (!text) return '';
        text = text.replace(/[\u064B-\u0652]/g, ''); // Remove diacritics
        text = text.replace(/[أإآ]/g, 'ا');
        text = text.replace(/ى/g, 'ي');
        text = text.replace(/ؤ/g, 'و');
        text = text.replace(/ئ/g, 'ي');
        text = text.replace(/ة/g, 'ه');
        return text;
    }

    // Fetch master list of books
    const fetchMasterList = () => fetch('./data/books.json')
        .then(res => res.ok ? res.json() : Promise.reject('Failed to load books.json'))
        .catch(err => {
            self.postMessage({ type: 'error', payload: { message: err.toString() } });
            return [];
        });

    // Fetch content of a single book part
    const fetchBookPart = (partFile) => fetch(`./data/${partFile}`)
        .then(res => res.ok ? res.json() : Promise.reject(`Failed to load ${partFile}`))
        .catch(err => {
            console.error(err);
            return null;
        });

    // Main function to build the search index
    async function buildSearchIndex() {
        try {
            const allBooks = await fetchMasterList();
            if (allBooks.length === 0) {
                self.postMessage({ type: 'error', payload: { message: "فشل تحميل قائمة الكتب." } });
                return;
            }

            const totalFilesToFetch = allBooks.reduce((acc, book) => acc + (book.parts ? book.parts.length : 1), 0);
            let filesProcessed = 0;
            let pageId = 0;
            self.postMessage({ type: 'progress', payload: { processed: 0, total: totalFilesToFetch } });

            for (const book of allBooks) {
                const filesToProcess = book.parts ? book.parts.map(p => p.file) : [`book_${book.id}.json`];
                
                for (const file of filesToProcess) {
                    const bookDetails = await fetchBookPart(file);
                    if (bookDetails && bookDetails.volumes) {
                        bookDetails.volumes.forEach(volume => {
                            volume.content?.forEach(page => {
                                const doc = {
                                    id: pageId++,
                                    bookId: book.id,
                                    bookTitle: book.title,
                                    volumeTitle: volume.volumeTitle,
                                    pageNumber: page.pageNumber,
                                    chapter: page.chapter,
                                    text: page.text,
                                    absoluteVolumeNumber: volume.volumeNumber
                                };
                                // Add to FlexSearch index with normalized text
                                index.add({
                                    ...doc,
                                    text: normalizeText(page.text),
                                    bookTitle: normalizeText(book.title),
                                    chapter: normalizeText(page.chapter),
                                });
                                // Store original content for snippet generation
                                searchableContent.push(doc);
                            });
                        });
                    }
                    filesProcessed++;
                    self.postMessage({ type: 'progress', payload: { processed: filesProcessed, total: totalFilesToFetch } });
                }
            }
            
            self.postMessage({ type: 'index-complete', payload: { searchableContent } });
        } catch (error) {
            self.postMessage({ type: 'error', payload: { message: error.toString() } });
        }
    }

    // Listen for messages from the main thread
    self.onmessage = async (event) => {
        const { type, payload } = event.data;

        if (type === 'build-index') {
            await buildSearchIndex();
        } else if (type === 'search') {
            const { query, bookId } = payload;
            const normalizedQuery = normalizeText(query);
            
            const searchOptions = {
                index: ['bookTitle', 'chapter', 'text'],
                enrich: true, // Returns full document
            };

            // Add a filter if a specific book is selected
            if (bookId !== 'all') {
                searchOptions.where = { bookId: parseInt(bookId) };
            }
            
            const results = await index.searchAsync(normalizedQuery, searchOptions);
            
            // FlexSearch returns results for each field. We need to flatten and get unique document IDs.
            const uniqueIds = new Set();
            results.forEach(fieldResult => {
                fieldResult.result.forEach(doc => {
                     uniqueIds.add(doc.id);
                });
            });

            self.postMessage({ type: 'search-results', payload: { results: Array.from(uniqueIds) } });
        }
    };
}

