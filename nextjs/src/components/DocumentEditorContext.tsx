import React, { createContext, useContext, useState, useCallback } from 'react';

interface DocumentEditorContextType {
  saveAndClose: () => Promise<void>;
  setSaveAndClose: (fn: () => Promise<void>) => void;
}

const DocumentEditorContext = createContext<DocumentEditorContextType | undefined>(undefined);

export const useDocumentEditor = () => {
  const context = useContext(DocumentEditorContext);
  if (!context) {
    throw new Error('useDocumentEditor must be used within a DocumentEditorProvider');
  }
  return context;
};

export const DocumentEditorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [saveAndClose, setSaveAndClose] = useState<() => Promise<void>>(() => async () => {});

  const contextValue = {
    saveAndClose,
    setSaveAndClose: useCallback((fn: () => Promise<void>) => setSaveAndClose(() => fn), []),
  };

  return (
    <DocumentEditorContext.Provider value={contextValue}>
      {children}
    </DocumentEditorContext.Provider>
  );
};