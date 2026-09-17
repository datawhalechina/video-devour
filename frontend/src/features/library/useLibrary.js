import { useEffect, useState } from "react";
import { readLibrary } from "./api";

export function useLibrary(query, scope) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setData(null);
    const timer = setTimeout(
      () =>
        readLibrary(query, scope, controller.signal)
          .then(setData)
          .catch((e) => {
            if (e.name !== "AbortError") setError(e.message);
          })
          .finally(() => {
            if (!controller.signal.aborted) setLoading(false);
          }),
      query.trim() ? 300 : 0,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, scope, revision]);
  return {
    data,
    loading,
    error,
    reload: () => setRevision((value) => value + 1),
  };
}
