export default function ImageBrowserPanel() {
  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Image Browser</h6>
      <p className="text-muted small">
        Generated images will appear here as a scrollable
        gallery. Click an image to load it onto the canvas
        or export it.
      </p>
      <div className="d-flex justify-content-center mt-3">
        <span className="text-muted" style={{ fontSize: "2rem" }}>
          🖼️
        </span>
      </div>
    </div>
  );
}
