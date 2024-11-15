"use client";
import React, { useState, useEffect } from "react";
import { get_url } from "@/utils/helpers";
import { Spinner } from "flowbite-react";
import { useDocumentEditor } from "@/components/document_editor/DocumentEditorContext";
import { DocumentEditor } from "@onlyoffice/document-editor-react";

interface Props {
  candidateId: string;
  onClose: () => void;
  type: string;
}

export default function DocumentEditorContainer({
  candidateId,
  onClose,
  type,
}: Props) {
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const { setSaveAndClose } = useDocumentEditor();
  const [docEditor, setDocEditor] = useState<any>(null);

  // Generate a unique document key that combines type and ID
  const documentKey = `${type}_${candidateId}`;

  useEffect(() => {
    const fetchToken = async () => {
      try {
        const tokenResponse = await fetch(get_url(`/project/onlyoffice/token/${type}/${candidateId}`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            documentKey: `${type}_${candidateId}`,
          })
        });
        
        const data = await tokenResponse.json();
        setToken(data.token);
        setBlobUrl(data.blob_url);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching token:', error);
        setIsLoading(false);
      }
    };

    fetchToken();
  }, [candidateId, type]);

  const config = {
    document: {
      fileType: "docx",
      key: documentKey,
      title: `${documentKey}.docx`,
      url: `${process.env.BACKEND_URL}/project/proxy_document?blob_url=${encodeURIComponent(blobUrl || '')}`,
      permissions: {
        chat: false,
        comment: false,
        commentGroups: [],
        copy: true,
        deleteCommentAuthorOnly: false,
        download: false,
        edit: true,
        editCommentAuthorOnly: false,
        fillForms: false,
        modifyContentControl: true,
        modifyFilter: false,
        print: false,
        protect: true,
        rename: false,
        review: true,
        reviewGroups: [],
        userInfoGroups: [],
      },
    },
    documentType: "word",
    editorConfig: {
      callbackUrl: `${process.env.BACKEND_URL}/project/onlyoffice/callback`,
      mode: "edit",
      user: {
        id: "anonymous",
        name: "User",
      },
      customization: {
        autosave: true,
        forcesave: true,
        comments: false,
        compactHeader: true,
        feedback: false,
        help: false,
      },
    },
    height: "100%",
    width: "100%",
    type: "desktop",
    events: {
      onAppReady: (evt: any) => {
        // Store reference to editor instance
        setDocEditor(evt.editor);
      },
      onDocumentReady: () => {
        console.log('Document is loaded and ready');
      },
      onError: (event: any) => {
        console.error('OnlyOffice error:', event);
      },
      onRequestClose: () => {
        onClose();
      },
    },
  };

  console.log(process.env.ONLY_OFFICE_URL);

  return (
    <div className="h-full w-full flex items-center justify-center">
      <div className="h-[90%] w-[90%]">
        {!isLoading && token && (
          <DocumentEditor
            id="docxEditor"
            documentServerUrl={"https://documents.talentkiwi.tech"}
            config={{...config, token}}
          />
        )}
      </div>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
          <Spinner size="xl" color="gray" />
        </div>
      )}
    </div>
  );
}
