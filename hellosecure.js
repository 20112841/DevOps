var fs = require('fs');

var options = {
    key: fs.readFileSync('private/webserver.key'),
    cert: fs.readFileSync('webserver.crt')
};

var https = require('https');

https.createServer(options, function (req, res) {
    res.writeHead(200);
    res.end('Secure hello from Node.js!');
    }).listen(4443);


