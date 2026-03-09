import { useCallback } from "react";

import { getApiValidationIssues, resolveApiErrorMessage } from "../api";

export function useApiError() {
  const getErrorMessage = useCallback((error, fallbackMessage) => {
    return resolveApiErrorMessage(error, fallbackMessage);
  }, []);

  const getValidationIssues = useCallback((error) => {
    return getApiValidationIssues(error);
  }, []);

  return {
    getErrorMessage,
    getValidationIssues,
  };
}
