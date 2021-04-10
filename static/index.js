var LOCAL_HOST = "http://localhost:8096";

var hideExp = function(){
    toggleExplanationContainer(false);

    helpBut = document.getElementById('helpfulButton');
    notHelpBut = document.getElementById('notHelpfulButton');
    helpBut.removeEventListener("click", logExp, true); 

    helpBut.removeEventListener("click", logExp, true); 
    notHelpBut.removeEventListener("contextmenu", logExp, true); 
    notHelpBut.removeEventListener("contextmenu", logExp, true); 
}

var tmpData = 
            {"json":{"explanation":"This section is about feedback for language modeling in the query likelihood model of information retrieval. Recall that we derive the query likelihood ranking function by making various assumptions, such as term independence. As a basic retrieval function, that family of functions worked well. However, if we think about incorporating feedback information, it is not immediately obvious how to modify 7.2 Feedback in Language Models 139 query likelihood to perform feedback. Many times, the feedback information is additional information about the query, but since we assumed that the query is generated by assembling words from an ideal document language model, we don't have an easy way to add this additional information. However, we have a way to generalize the query likelihood function that will allow us to include feedback documents more easily: it's called a Kullback-Leibler <span style=\"background-color: #bddcf5\">divergence</span> retrieval model, or <span style=\"background-color: #bddcf5\">KL</span>-<span style=\"background-color: #bddcf5\">divergence</span> retrieval model for short. This model actually makes the query likelihood retrieval function much closer to the vector space model. Despite this, the new form of the language model retrieval can still be regarded as a generalization of query likelihood (in that it covers query likelihood without feedback as a special case). Here, the feedback can be achieved through query model estimation or updating. This is very similar to Rocchio feedback which updates the query vector; in this case, we update the query language model instead. Figure 7.3 shows the difference between our original query likelihood formula and the generalized <span style=\"background-color: #bddcf5\">KL</span>-<span style=\"background-color: #bddcf5\">divergence</span> model. On top, we have the query likelihood retrieval function. The <span style=\"background-color: #bddcf5\">KL</span>-<span style=\"background-color: #bddcf5\">divergence</span> retrieval model generalizes the query term frequency into a probabilistic distribution. This distribution is the only difference, which is able to characterize the user's query in a more general way. This query language model can be estimated in many different ways-including using feedback information. This method is called <span style=\"background-color: #bddcf5\">KL</span>-<span style=\"background-color: #bddcf5\">divergence</span> because this can be interpreted as measuring the <span style=\"background-color: #bddcf5\">divergence</span> (i.e., difference) between two distributions; one is the query model p(w |\u03b8 Q ) and the other is the document language model from before. We won't go into detail on <span style=\"background-color: #bddcf5\">KL</span>-<span style=\"background-color: #bddcf5\">divergence</span>, but there is a more detailed explanation in appendix C.","file_names":"122.txt","num_results":1}};

var test = function(){
    return "blah";
}

// var socket = io.connect('http://' + document.domain + ':' + location.port);
// console.log("io",io)

$(document).ready(function(){
    var socket = io()
    socket.connect(`${LOCAL_HOST}/`, {transports: ['websocket']});

    socket.on('message', function(searchString) {
        console.log("1")
        console.log(searchString)
        doSearch(searchString);
    });
    socket.on('google-search-result', function(searchResults) {
        displayGoogleSearch(searchResults);
    });
    toggleNoExplainText(false);
    toggleExplanationContainer(false);
});

var logExp = function(isHelpful,expId,expTerm){
    logdata = JSON.stringify({
        action: isHelpful+'###EXP_###'+expTerm+'###'+expId,
        route: window.location.pathname
    });
    navigator.sendBeacon(`${LOCAL_HOST}/log_action`, logdata);

}

var toggleNoExplainText = function(isVisible) {
    displayMode = isVisible ? "block" : "none";
    $("#no-explain-text").css("display", displayMode);
}

var toggleExplanationContainer = function(isVisible) {
    displayMode = isVisible ? "block" : "none";
    $("#docs-div").css("display", displayMode);
    $("#helpfulButton").css("display", displayMode);
    $("#notHelpfulButton").css("display", displayMode);
}

var googleResultItemHTML = (result) => {
    item = document.createElement("li");
    item.innerHTML =`
        <a href=${result.link}><h5>${result.title}</h5></a>
        <p>${result.htmlSnippet}</p>
    `
    return item;
}

var googleResultsListHMTL = (results) => {
    searchList = document.createElement("ul");
    searchList.className = "scrollable-search-list";
    for (result of results) {
        searchList.appendChild(googleResultItemHTML(result));
    }
    return searchList;
}

var displayGoogleSearch = function(results) {
    resultHTML = googleResultsListHMTL(results);
    document.getElementById("google-search-div").appendChild(resultHTML);
}

var googleSearchExp = function() {
    $("#google-search-div").empty();
    query = document.getElementById("search-explanation").getAttribute("data-query");
    if (query.length > 0) {
        googleQueryExplanation(query)
            .then((results)=> {
                displayGoogleSearch(results);
            })
    }
}

var doGoogleSearch = function() {
    query = document.getElementById("search-explanation").getAttribute("data-query");
    if (query.length > 0) {
        googleQueryExplanation(query)
            .then((results)=> {
                var xhttp = new XMLHttpRequest();
                    xhttp.onreadystatechange = function() {
                };

                xhttp.open("POST", `${LOCAL_HOST}/google-search`, true);
                var text = window.getSelection().toString();
                xhttp.setRequestHeader("Content-type", "application/json;charset=utf-8");
                xhttp.send(JSON.stringify({ 'results':  results }));
            })
    }
}

var doSearch = function(searchString) {
    const data = {
        "searchString": searchString,
    }
    console.log("2")
    console.log(searchString)
    if (searchString!='')
    {

        var num_fetched_res = 0
        /*fetch("http://timan102.cs.illinois.edu/explanation//search", {
        // fetch("http://expertsearch.centralus.cloudapp.azur`1e.com/search", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data)
    })*/
        new Promise((resolve) => {
                resolve(tmpData);
        })
            .then(data => {
                data = data.json;
                console.log("bbb",data)

                const doc = data.explanation;

                if (data.num_results==1){
                    toggleExplanationContainer(true);
                    toggleNoExplainText(false);
                    document.getElementById("explain_title").innerHTML = `Explanation for ${searchString}`;
                    document.getElementById("explain_div").innerHTML = doc; 
                    document.getElementById("search-explanation").setAttribute("data-query", searchString);
                    helpBut = document.getElementById('helpfulButton');
                    notHelpBut = document.getElementById('notHelpfulButton');
                    helpBut.addEventListener('click', function() {
                        logExp('1',data.file_names,searchString);
                    } , true);

                    helpBut.addEventListener('contextmenu', function() {
                        logExp('1',data.file_names,searchString);
                    } , true);

                    notHelpBut.addEventListener('click', function() {
                        logExp('0',data.file_names,searchString);
                    } , true);
                    notHelpBut.addEventListener('contextmenu', function() {
                        logExp('0',data.file_names,searchString);
                    } , true);
                }
                else{
                    toggleExplanationContainer(false);
                    toggleNoExplainText(true);
                }

            }
            );
    }
}



