const GAS_URL = "https://script.google.com/macros/s/AKfycbzfTqKJqm4fwp-LfYBhBe9vJOPSVKT_oAUy0gDrjet3aSYrg9Sz5OWVhXhD1qllyq5y/exec";

async function searchCustomer() {
    const queryValue = document.getElementById('queryInput').value;
    
    // أولاً: نجلب التوكن عبر جوجل
    const tokenResponse = await fetch(GAS_URL, {
        method: 'POST',
        body: JSON.stringify({ action: "getToken" })
    });
    const tokenData = await tokenResponse.json();
    const token = tokenData.access_token;

    // ثانياً: نبحث عن المشترك
    const searchResponse = await fetch(GAS_URL, {
        method: 'POST',
        body: JSON.stringify({
            action: "search",
            token: token,
            queryParam: "name",
            value: queryValue
        })
    });
    const results = await searchResponse.json();
    console.log(results); // هنا ستعرض النتائج في الجداول كما في تصميمك
}