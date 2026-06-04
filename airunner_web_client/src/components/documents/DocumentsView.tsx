import Card from "react-bootstrap/Card";
import Alert from "react-bootstrap/Alert";

export default function DocumentsView() {
  return (
    <div>
      <h3 className="mb-3">📄 Documents</h3>
      <Card body>
        <Alert variant="info">
          Document upload and RAG indexing will be available when the services
          endpoint is ready. Documents are managed on the daemon side.
        </Alert>
        <p className="text-muted">
          To add documents for RAG (Retrieval-Augmented Generation), upload
          files through the daemon's document management API. Supported
          formats: PDF, EPUB, MOBI, HTML, Markdown, ZIM.
        </p>
      </Card>
    </div>
  );
}
