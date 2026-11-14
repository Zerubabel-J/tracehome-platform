// CloudFront Function (runtime cloudfront-js-2.0), attached to the DEFAULT behavior only
// (the web bucket), on viewer request.
//
// App routes such as /listings/42 aren't files in the bucket. Without this, S3 answers 403.
// We rewrite any path without a file extension to /index.html, and the React router takes over.
//
// Why not a CloudFront "custom error response" (403 -> /index.html)? Those apply to the whole
// distribution, so they would also replace the API's real 403 and 404 answers with the website.
function handler(event) {
  var request = event.request;
  var lastSegment = request.uri.split("/").pop();
  if (lastSegment.indexOf(".") === -1) {
    request.uri = "/index.html";
  }
  return request;
}
