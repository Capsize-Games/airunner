import { useState, useEffect } from "react";
import Card from "react-bootstrap/Card";
import Table from "react-bootstrap/Table";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import { startHuggingFaceDownload, getBootstrapData } from "../../api/client";
import type { BootstrapData } from "../../types/api";

export default function DownloadManager() {
  const [bootstrap, setBootstrap] = useState<BootstrapData | null>(null);
  const [downloading, setDownloading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getBootstrapData().then(setBootstrap).catch(() => {});
  }, []);

  const handleDownload = async (repoId: string, modelType = "llm") => {
    if (downloading[repoId]) return;
    setDownloading((d) => ({ ...d, [repoId]: true }));
    try {
      await startHuggingFaceDownload(repoId, modelType);
    } catch {
      // ignore
    } finally {
      setDownloading((d) => ({ ...d, [repoId]: false }));
    }
  };

  const models = bootstrap?.models ?? [];
  const llmModels = models.filter(
    (m: Record<string, unknown>) => m.category === "llm",
  );
  const artModels = models.filter(
    (m: Record<string, unknown>) =>
      m.category !== "llm" &&
      (!m.pipeline_action || m.pipeline_action !== "embedding"),
  );

  return (
    <div>
      <h3 className="mb-3">⬇️ Available Models</h3>

      <Card className="mb-3">
        <Card.Header>🤖 LLM Models</Card.Header>
        <Table striped hover size="sm">
          <thead>
            <tr>
              <th>Name</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {llmModels.map((m: Record<string, unknown>, i: number) => (
              <tr key={i}>
                <td>
                  {String(m.version ?? m.name ?? m.path ?? `Model #${i}`)}
                </td>
                <td>
                  <Button
                    size="sm"
                    variant="outline-primary"
                    onClick={() =>
                      handleDownload(String(m.path ?? ""), "llm")
                    }
                    disabled={downloading[String(m.path ?? "")] ?? false}
                  >
                    {downloading[String(m.path ?? "")] ? (
                      <Spinner animation="border" size="sm" />
                    ) : (
                      "Download"
                    )}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card className="mb-3">
        <Card.Header>🎨 Art Models</Card.Header>
        <Table striped hover size="sm">
          <thead>
            <tr>
              <th>Name</th>
              <th>Version</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {artModels.map((m: Record<string, unknown>, i: number) => (
              <tr key={i}>
                <td>{String(m.version ?? m.name ?? `Model #${i}`)}</td>
                <td>{String(m.version ?? "—")}</td>
                <td>
                  <Button
                    size="sm"
                    variant="outline-primary"
                    onClick={() =>
                      handleDownload(String(m.path ?? ""), "art")
                    }
                    disabled={downloading[String(m.path ?? "")] ?? false}
                  >
                    {downloading[String(m.path ?? "")] ? (
                      <Spinner animation="border" size="sm" />
                    ) : (
                      "Download"
                    )}
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
