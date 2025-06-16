"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import axios from "axios";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import { useAuth } from "@/src/supabase-auth-context";

export default function RefinePage() {
  const { fileId } = useParams();
  const router = useRouter();
  const { user, loading, session } = useAuth();
  const [entry, setEntry] = useState<any>(null);
  const [entryLoading, setEntryLoading] = useState(false);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [fields, setFields] = useState<any>({});

  // Admin route protection
  useEffect(() => {
    if (!loading && session?.access_token) {
      router.replace("/admin");
    }
  }, [session?.access_token, loading, router]);

  // Fetch a random entry
  const fetchRandomEntry = useCallback(() => {
    if (session?.access_token) {
      setEntryLoading(true);
      setEntryError(null);
      axios
        .post(`/api/wine-lists/${fileId}/refinement/random`, {}, {
          headers: { Authorization: `Bearer ${session?.access_token}` }
        })
        .then((res) => {
          setEntry(res.data);
          setFields(res.data);
        })
        .catch((err) => {
          setEntryError(err.response?.data?.detail || err.message || "Failed to load entry");
          setEntry(null);
        })
        .finally(() => setEntryLoading(false));
    }
  }, [fileId, session?.access_token]);

  useEffect(() => {
    fetchRandomEntry();
  }, [fetchRandomEntry]);

  // Handlers for field changes
  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFields({ ...fields, [e.target.name]: e.target.value });
  };

  // Refine with AI
  const handleRefineAI = () => {
    if (!entry || !session?.access_token) return;
    setEntryLoading(true);
    setEntryError(null);
    axios
      .post(`/api/wine-entries/${entry.id}/refine/ai`, {}, {
        headers: { Authorization: `Bearer ${session?.access_token}` }
      })
      .then((res) => {
        setFields(res.data);
      })
      .catch((err) => {
        setEntryError(err.response?.data?.detail || err.message || "AI refinement failed");
      })
      .finally(() => setEntryLoading(false));
  };

  // Refine with LWIN
  const handleRefineLWIN = () => {
    if (!entry || !session?.access_token) return;
    setEntryLoading(true);
    setEntryError(null);
    axios
      .post(`/api/wine-entries/${entry.id}/refine/lwin`, {}, {
        headers: { Authorization: `Bearer ${session?.access_token}` }
      })
      .then((res) => {
        setFields(res.data);
      })
      .catch((err) => {
        setEntryError(err.response?.data?.detail || err.message || "LWIN refinement failed");
      })
      .finally(() => setEntryLoading(false));
  };

  // Save manual changes
  const handleSave = () => {
    if (!entry || !session?.access_token) return;
    setEntryLoading(true);
    setEntryError(null);
    axios
      .post(`/api/wine-lists/${fileId}/refinement/update`, {
        entry_id: entry.id,
        fields: fields
      }, {
        headers: { Authorization: `Bearer ${session?.access_token}` }
      })
      .then(() => {
        fetchRandomEntry();
      })
      .catch((err) => {
        setEntryError(err.response?.data?.detail || err.message || "Save failed");
      })
      .finally(() => setEntryLoading(false));
  };

  // Next entry
  const handleNext = () => {
    fetchRandomEntry();
  };

  if (entryLoading) return <div className="p-8">Loading...</div>;
  if (entryError) return <div className="p-8 text-red-500">{entryError}</div>;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-8">
          <h1 className="text-2xl font-bold mb-6">Refine Wine Entry</h1>
          {entry && (
            <form className="max-w-2xl space-y-4">
              <div>
                <label className="block font-semibold">Raw Text</label>
                <textarea
                  className="w-full border rounded p-2 text-xs"
                  name="raw_text"
                  value={fields.raw_text || ""}
                  onChange={handleFieldChange}
                  rows={3}
                  readOnly
                />
              </div>
              {['producer','cuvee','vintage','price','bottle_size','grape_variety','country','region','subregion','designation','classification','sub_type','type'].map((field) => (
                <div key={field}>
                  <label className="block font-semibold capitalize">{field.replace('_', ' ')}</label>
                  <input
                    className="w-full border rounded p-2 text-sm"
                    name={field}
                    value={fields[field] || ""}
                    onChange={handleFieldChange}
                  />
                </div>
              ))}
              <div className="flex gap-2 mt-4">
                <button type="button" className="bg-blue-600 text-white px-4 py-2 rounded" onClick={handleRefineAI}>Refine with AI</button>
                <button type="button" className="bg-purple-600 text-white px-4 py-2 rounded" onClick={handleRefineLWIN}>Match to LWIN</button>
                <button type="button" className="bg-green-600 text-white px-4 py-2 rounded" onClick={handleSave}>Save</button>
                <button type="button" className="bg-gray-400 text-white px-4 py-2 rounded" onClick={handleNext}>Next</button>
              </div>
            </form>
          )}
        </main>
      </div>
    </div>
  );
} 