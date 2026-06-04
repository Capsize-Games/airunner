import { useState, useCallback, useEffect } from "react";
import Konva from "konva";
import type { PendingDrop } from "./CanvasPanelTypes";
import { IMAGE_MAGIC } from "./CanvasPanelTypes";
import { fitDimensions } from "../../../features/canvas/ImageDropModal";
import type { DropResizeMode } from "../../../features/canvas/ImageDropModal";

export function useCanvasImageDrop(
  stageRef: React.RefObject<Konva.Stage>,
) {
  const [pendingDrop, setPendingDrop] = useState<PendingDrop | null>(
    null,
  );
  const [showDropModal, setShowDropModal] = useState(false);

  const canvasDropPos = useCallback(
    (clientX: number, clientY: number) => {
      const stage = stageRef.current;
      if (!stage) return { x: 0, y: 0 };
      const rect = stage.container().getBoundingClientRect();
      const scale = stage.scaleX();
      return {
        x: (clientX - rect.left - stage.x()) / scale,
        y: (clientY - rect.top - stage.y()) / scale,
      };
    },
    [stageRef],
  );

  const queueDrop = useCallback(
    (dataUrl: string, x: number, y: number) => {
      const img = new Image();
      img.onload = () => {
        setPendingDrop({
          base64: dataUrl,
          x,
          y,
          naturalW: img.naturalWidth,
          naturalH: img.naturalHeight,
        });
        setShowDropModal(true);
      };
      img.src = dataUrl;
    },
    [],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  /** Check whether a file is an image using MIME type (fast) or magic bytes. */
  const isImageFile = useCallback(
    async (file: File): Promise<boolean> => {
      if (file.type.startsWith("image/")) return true;
      try {
        const buf = await file.slice(0, 8).arrayBuffer();
        const header = new Uint8Array(buf);
        return IMAGE_MAGIC.some(([sig, len]) =>
          sig.every((byte, i) => header[i] === byte),
        );
      } catch {
        return false;
      }
    },
    [],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const { x, y } = canvasDropPos(e.clientX, e.clientY);

      const file = e.dataTransfer.files[0];
      if (file) {
        isImageFile(file).then((isImage) => {
          if (!isImage) {
            const imageUrl = e.dataTransfer.getData("text/image-url");
            if (imageUrl) {
              fetch(imageUrl)
                .then((r) => r.blob())
                .then((blob) => {
                  const r2 = new FileReader();
                  r2.onload = (ev) => {
                    const dataUrl = ev.target?.result as string;
                    if (dataUrl) queueDrop(dataUrl, x, y);
                  };
                  r2.readAsDataURL(blob);
                })
                .catch(() => {
                  /* silently ignore */
                });
            }
            return;
          }
          const reader = new FileReader();
          reader.onload = (ev) => {
            const dataUrl = ev.target?.result as string;
            if (dataUrl) queueDrop(dataUrl, x, y);
          };
          reader.readAsDataURL(file);
        });
        return;
      }

      const imageUrl = e.dataTransfer.getData("text/image-url");
      if (imageUrl) {
        fetch(imageUrl)
          .then((r) => r.blob())
          .then((blob) => {
            const reader = new FileReader();
            reader.onload = (ev) => {
              const dataUrl = ev.target?.result as string;
              if (dataUrl) queueDrop(dataUrl, x, y);
            };
            reader.readAsDataURL(blob);
          })
          .catch(() => {
            /* silently ignore */
          });
      }
    },
    [canvasDropPos, queueDrop, isImageFile],
  );

  const handleDropConfirm = useCallback(
    (
      mode: DropResizeMode,
      pendingDrop: PendingDrop,
      activeGridArea: { width: number; height: number },
      documentWidth: number,
      documentHeight: number,
      placeImageFn: (
        base64: string,
        x: number,
        y: number,
        w: number,
        h: number,
      ) => void,
    ) => {
      const { base64, x, y, naturalW, naturalH } = pendingDrop;
      let w = naturalW;
      let h = naturalH;
      if (mode === "fit-grid") {
        const fit = fitDimensions(
          naturalW,
          naturalH,
          activeGridArea.width,
          activeGridArea.height,
        );
        w = fit.w;
        h = fit.h;
      } else if (mode === "fit-canvas") {
        const fit = fitDimensions(
          naturalW,
          naturalH,
          documentWidth,
          documentHeight,
        );
        w = fit.w;
        h = fit.h;
      }
      placeImageFn(
        base64,
        Math.max(0, x - w / 2),
        Math.max(0, y - h / 2),
        w,
        h,
      );
      setPendingDrop(null);
    },
    [],
  );

  /** Listen for the "canvas-place-image" event fired by ServerImageRow */
  const useCanvasPlaceImage = (queueDropFn: typeof queueDrop) => {
    useEffect(() => {
      const handler = (e: Event) => {
        const { imageUrl } = (
          e as CustomEvent<{ imageUrl: string }>
        ).detail;
        if (!imageUrl) return;
        fetch(imageUrl)
          .then((r) => r.blob())
          .then((blob) => {
            const reader = new FileReader();
            reader.onload = (ev) => {
              const dataUrl = ev.target?.result as string;
              if (dataUrl) queueDropFn(dataUrl, 0, 0);
            };
            reader.readAsDataURL(blob);
          })
          .catch(() => {
            /* silently ignore */
          });
      };
      window.addEventListener("canvas-place-image", handler);
      return () =>
        window.removeEventListener("canvas-place-image", handler);
    }, [queueDropFn]);
  };

  return {
    pendingDrop,
    showDropModal,
    setShowDropModal,
    canvasDropPos,
    queueDrop,
    handleDragOver,
    isImageFile,
    handleDrop,
    handleDropConfirm,
    useCanvasPlaceImage,
  };
}
