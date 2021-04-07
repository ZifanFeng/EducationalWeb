const GOOGLE_SEARCH_API = `https://content.googleapis.com/discovery/v1/apis/customsearch/v1/rest` 
const CX = "e21570fed0b80d48e";
const API_KEY = "<API>";
function init() {
    console.log("init client")
    gapi.client.setApiKey(API_KEY);
    gapi.client.load(GOOGLE_SEARCH_API)
        .then(() => { console.log("GAPI client loaded for API"); })
        .catch( (err) => { console.error("Error loading GAPI client for API", err); });
}
function search(query) {
    return gapi.client.search.cse.list({
        "cx": CX,
        "q": query
    })
        .then((response) => {
            // Handle the results here (response.result has the parsed body).
            console.log("Response", response);
        })
        .catch( (err) => { console.error("Execute error", err); });
}

gapi.load("client", init);
