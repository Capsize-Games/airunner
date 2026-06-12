import { useState, useRef, useEffect, useCallback } from "react";

interface AnchorPoint {
  left: number;
  bottom: number;
}

interface DropdownAnchor {
  left: number;
  bottom: number;
  minWidth: number;
}

export function useArtOverlays() {
  // ── Model options popup ──
  const [showModelOptions, setShowModelOptions] = useState(false);
  const modelOptionsBtnRef = useRef<HTMLDivElement>(null);
  const [modelOptionsAnchor, setModelOptionsAnchor] =
    useState<AnchorPoint | null>(null);

  useEffect(() => {
    if (!showModelOptions) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (modelOptionsBtnRef.current?.contains(target)) return;
      if (
        document
          .getElementById("art-model-options-popup")
          ?.contains(target)
      )
        return;
      const dropdownPortals = document.querySelectorAll(
        "[data-dropdown-portal]",
      );
      for (const portal of dropdownPortals) {
        if (portal.contains(target)) return;
      }
      setShowModelOptions(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showModelOptions]);

  // ── Size picker ──
  const sizePortalId = useRef(
    `size-portal-${Math.random().toString(36).slice(2, 8)}`,
  ).current;
  const [showSize, setShowSize] = useState(false);
  const sizeBtnRef = useRef<HTMLDivElement>(null);
  const [sizeAnchor, setSizeAnchor] = useState<AnchorPoint | null>(
    null,
  );
  const sizeEmittingRef = useRef(false);

  useEffect(() => {
    if (!showSize) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const portalEl = document.getElementById(sizePortalId);
      if (portalEl?.contains(target)) return;
      if (
        sizeBtnRef.current &&
        !sizeBtnRef.current.contains(target)
      )
        setShowSize(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showSize, sizePortalId]);

  useEffect(() => {
    const handler = () => {
      if (sizeEmittingRef.current) return;
      setShowSize(false);
    };
    window.addEventListener("art-overlay-opened", handler);
    window.addEventListener("chat-picker-opened", handler);
    return () => {
      window.removeEventListener("art-overlay-opened", handler);
      window.removeEventListener("chat-picker-opened", handler);
    };
  }, []);

  // ── Generation type picker ──
  const [showGenType, setShowGenType] = useState(false);
  const genTypeBtnRef = useRef<HTMLDivElement>(null);
  const [genTypeAnchor, setGenTypeAnchor] =
    useState<AnchorPoint | null>(null);
  const genTypeEmittingRef = useRef(false);

  useEffect(() => {
    if (!showGenType) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (genTypeBtnRef.current?.contains(target)) return;
      if (
        document
          .getElementById("art-gen-type-popup")
          ?.contains(target)
      )
        return;
      setShowGenType(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showGenType]);

  useEffect(() => {
    const handler = () => {
      if (genTypeEmittingRef.current) return;
      setShowGenType(false);
    };
    window.addEventListener("art-overlay-opened", handler);
    return () =>
      window.removeEventListener("art-overlay-opened", handler);
  }, []);

  // ── Info dropdown ──
  const [dropdownField, setDropdownField] = useState<string | null>(
    null,
  );
  const [dropdownAnchor, setDropdownAnchor] =
    useState<DropdownAnchor | null>(null);
  const dropdownEmittingRef = useRef(false);

  useEffect(() => {
    if (!dropdownField) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        document
          .getElementById("art-info-dropdown-popup")
          ?.contains(target)
      )
        return;
      const dropdownPortals = document.querySelectorAll(
        "[data-dropdown-portal]",
      );
      for (const portal of dropdownPortals) {
        if (portal.contains(target)) return;
      }
      setDropdownField(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownField]);

  useEffect(() => {
    const handler = () => {
      if (dropdownEmittingRef.current) return;
      setDropdownField(null);
    };
    window.addEventListener("art-overlay-opened", handler);
    return () =>
      window.removeEventListener("art-overlay-opened", handler);
  }, []);

  // ── GenInfo size popup ──
  const genSizePortalId = "art-gen-size-popup";
  const [showGenSize, setShowGenSize] = useState(false);
  const [genSizeAnchor, setGenSizeAnchor] = useState<AnchorPoint | null>(
    null,
  );

  useEffect(() => {
    if (!showGenSize) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const portalEl = document.getElementById(genSizePortalId);
      if (portalEl?.contains(target)) return;
      setShowGenSize(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showGenSize]);

  useEffect(() => {
    const handler = () => setShowGenSize(false);
    window.addEventListener("art-overlay-opened", handler);
    return () =>
      window.removeEventListener("art-overlay-opened", handler);
  }, []);

  const toggleGenSize = useCallback(
    (anchorRect?: DOMRect) => {
      const next = !showGenSize;
      setShowGenSize(next);
      if (next && anchorRect) {
        setGenSizeAnchor({
          left: anchorRect.left + 110,
          bottom: window.innerHeight - anchorRect.top + 4,
        });
      }
    },
    [showGenSize],
  );

  // ── Toggle helpers ──
  const toggleModelOptions = useCallback(() => {
    const next = !showModelOptions;
    setShowModelOptions(next);
    if (next && modelOptionsBtnRef.current) {
      const r = modelOptionsBtnRef.current.getBoundingClientRect();
      setModelOptionsAnchor({
        left: r.left,
        bottom: window.innerHeight - r.top + 4,
      });
    }
  }, [showModelOptions]);

  const toggleSize = useCallback(() => {
    const next = !showSize;
    setShowSize(next);
    if (next) {
      sizeEmittingRef.current = true;
      window.dispatchEvent(new Event("art-overlay-opened"));
      sizeEmittingRef.current = false;
      if (sizeBtnRef.current) {
        const r = sizeBtnRef.current.getBoundingClientRect();
        setSizeAnchor({
          left: r.left,
          bottom: window.innerHeight - r.top + 4,
        });
      }
    }
  }, [showSize]);

  const toggleGenType = useCallback(() => {
    const next = !showGenType;
    setShowGenType(next);
    if (next) {
      genTypeEmittingRef.current = true;
      window.dispatchEvent(new Event("art-overlay-opened"));
      genTypeEmittingRef.current = false;
      if (genTypeBtnRef.current) {
        const r = genTypeBtnRef.current.getBoundingClientRect();
        setGenTypeAnchor({
          left: r.left,
          bottom: window.innerHeight - r.top + 4,
        });
      }
    }
  }, [showGenType]);

  const openDropdown = useCallback(
    (field: string, anchorRect: DOMRect) => {
      // Toggle: if the same field is already open, close it.
      if (dropdownField === field) {
        setDropdownField(null);
        return;
      }
      dropdownEmittingRef.current = true;
      window.dispatchEvent(new Event("art-overlay-opened"));
      dropdownEmittingRef.current = false;
      setDropdownAnchor({
        left: anchorRect.left + 100,
        bottom: window.innerHeight - anchorRect.top + 4,
        minWidth: anchorRect.width - 100,
      });
      setDropdownField(field);
    },
    [dropdownField],
  );

  const closeDropdown = useCallback(
    () => setDropdownField(null),
    [],
  );

  const closeGenType = useCallback(() => setShowGenType(false), []);

  return {
    showModelOptions,
    modelOptionsBtnRef,
    modelOptionsAnchor,
    sizePortalId,
    showSize,
    sizeBtnRef,
    sizeAnchor,
    showGenType,
    genTypeBtnRef,
    genTypeAnchor,
    dropdownField,
    dropdownAnchor,
    showGenSize,
    genSizeAnchor,
    genSizePortalId,
    toggleModelOptions,
    toggleSize,
    toggleGenType,
    toggleGenSize,
    openDropdown,
    closeDropdown,
    closeGenType,
  };
}
