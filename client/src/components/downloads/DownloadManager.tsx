import { useState, useEffect } from "react";
import Card from "react-bootstrap/Card";
import Table from "react-bootstrap/Table";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import { listLLMModels, startHuggingFaceDownload } from "../../api/client";

interface ModelOption {
  label: string;
  value: string;
  pipeline_action: string;
}

export default function DownloadManager() {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [downloading, setDownloading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    listLLMModels().then(setModels).catch(() => {});
  }, []);

  const handleDownload = async (repoId: string) => {
    if (downloading[repoId]) return;
    setDownloading((d) => ({ ...d, [repoId]: true }));
    try {
      await startHuggingFaceDownload(repoId, "llm");
    } finally {
      setDownloading((d) => ({ ...d, [repoId]: false }));
    }
  };

  const llmModels = models.filter(
    (m) => m.pipeline_action !== "embedding",
  );

  return (
    <div>
      <h3 className="mb-3">⬇️ Available Models</h3>
      <Card>
        <Card.Header>🤖 LLM Models</Card.Header>
        <Table striped hover size="sm">
          <thead>
            <tr><th>Name</th><th>Action</th></tr>
          </thead>
          <tbody>
            {llmModels.map((m, i) => (
              <tr key={i}>
                <td>{m.label}</td>
                <td>
                  <Button
                    size="sm"
                    variant="outline-primary"
                    onClick={() => handleDownload(m.value)}
                    disabled={downloading[m.value] ?? false}
                  >
                    {downloading[m.value]
                      ? <Spinner animation="border" size="sm" />
                      : "Download"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
