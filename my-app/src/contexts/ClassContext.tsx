import { createContext, useState, useEffect, useCallback, useContext, type ReactNode } from "react";
import { classesApi } from "@/api/classes";
import type { ClassInfo } from "@/types/class";

interface ClassContextValue {
  currentClass: ClassInfo | null;
  classes: ClassInfo[];
  setCurrentClass: (c: ClassInfo) => void;
  loading: boolean;
  refetchClasses: () => Promise<void>;
}

const ClassContext = createContext<ClassContextValue | null>(null);

export function ClassProvider({ children }: { children: ReactNode }) {
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [currentClass, setCurrentClassState] = useState<ClassInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchClasses = useCallback(async () => {
    setLoading(true);
    try {
      const res = await classesApi.list();
      setClasses(res.items);

      // Restore persisted selection if valid
      const savedId = localStorage.getItem("currentClassId");
      if (savedId) {
        const found = res.items.find((c) => c.id === Number(savedId));
        if (found) {
          setCurrentClassState(found);
        } else if (res.items.length > 0) {
          setCurrentClassState(res.items[0]);
          localStorage.setItem("currentClassId", String(res.items[0].id));
        }
      } else if (res.items.length > 0) {
        setCurrentClassState(res.items[0]);
        localStorage.setItem("currentClassId", String(res.items[0].id));
      }
    } catch {
      // Ignore errors silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClasses();
  }, [fetchClasses]);

  const setCurrentClass = useCallback((c: ClassInfo) => {
    setCurrentClassState(c);
    localStorage.setItem("currentClassId", String(c.id));
  }, []);

  return (
    <ClassContext value={{
      currentClass,
      classes,
      setCurrentClass,
      loading,
      refetchClasses: fetchClasses,
    }}>
      {children}
    </ClassContext>
  );
}

export function useClassContext(): ClassContextValue {
  const context = useContext(ClassContext);
  if (!context) {
    throw new Error("useClassContext must be used within a ClassProvider");
  }
  return context;
}
