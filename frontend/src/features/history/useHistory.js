import { useCallback, useEffect, useState } from "react";
import { getHistory, deleteReport } from "../../api/videoService";

export function useHistory() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRecords(await getHistory());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    let active = true;
    getHistory()
      .then((data) => {
        if (active) setRecords(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  const hasActive = records.some((item) => item.status === "processing");
  useEffect(() => {
    if (!hasActive) return;
    let active = true;
    const timer = setInterval(
      () =>
        getHistory()
          .then((data) => {
            if (active) setRecords(data);
          })
          .catch(() => {}),
      5000,
    );
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [hasActive]);
  const remove = async (id) => {
    await deleteReport(id);
    setRecords((items) => items.filter((item) => item.id !== id));
  };
  return { records, loading, error, refresh, remove };
}
