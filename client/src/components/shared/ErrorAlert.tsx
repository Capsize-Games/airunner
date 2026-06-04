import Alert from "react-bootstrap/Alert";

export function ErrorAlert({ message }: { message: string }) {
  return (
    <Alert variant="danger" dismissible className="mt-2">
      {message}
    </Alert>
  );
}
