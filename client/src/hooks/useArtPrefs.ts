import { useLocalStorage } from "./useLocalStorage";

export function useArtPrefs() {
  const [artModel, setArtModel] = useLocalStorage("airunner_art_model", "");
  const [artVersion, setArtVersion] = useLocalStorage("airunner_art_version", "");
  const [seed, setSeed] = useLocalStorage("airunner_seed", "");

  return { artModel, setArtModel, artVersion, setArtVersion, seed, setSeed };
}
