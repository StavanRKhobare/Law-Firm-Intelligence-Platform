import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from '../services/api';

/** Load data when `deps` change. Stale responses are ignored. */
export function useFetch(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const latest = useRef(0);

  const reload = useCallback(async () => {
    const call = ++latest.current;
    setLoading(true);
    try {
      const response = await fetcher();
      if (call === latest.current) {
        setData(response.data);
        setError('');
      }
    } catch (e) {
      if (call === latest.current) setError(errorMessage(e, 'Could not load this. Please try again.'));
    } finally {
      if (call === latest.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { reload(); }, [reload]);

  return { data, error, loading, reload };
}

/** Holds a value and only settles after the user stops typing. */
export function useDebounced(value, delay = 300) {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}
