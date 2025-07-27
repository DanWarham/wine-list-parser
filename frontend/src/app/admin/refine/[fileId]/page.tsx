"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import axios from "axios";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import { useAuth } from "@/src/supabase-auth-context";
import { api } from "@/utils/api_v2";

export default function RefinePage() {
  const { fileId } = useParams();
  const router = useRouter();
  const { user, loading, session } = useAuth();
  const [entry, setEntry] = useState<any>(null);
  const [entryLoading, setEntryLoading] = useState(false);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [fields, setFields] = useState<any>({});
  const [roleChecked, setRoleChecked] = useState(false);

  // Admin route protection
  useEffect(() => {
    const checkRole = async () => {
      if (loading) return; // Wait for auth to be ready
      
      if (!user || !session) {
        router.push('/login')
        return
      }

      try {
        const userInfo = await api.getCurrentUser(session.access_token)
        if (userInfo.role !== 'admin') {
          router.push('/search')
        } else {
          setRoleChecked(true)
        }
      } catch (error) {
        console.error('Role check failed:', error)
        router.push('/login')
      }
    }
    checkRole()
  }, [user, loading, router, session])

  // Fetch a random entry
  const fetchRandomEntry = useCallback(() => {
    if (session?.access_token) {
      setEntryLoading(true);
      setEntryError(null);
      // Get all wine entries for this file
      api.getWineEntries(session.access_token, fileId as string)
        .then((entries) => {
          if (entries.length > 0) {
            // Pick a random entry
            const randomEntry = entries[Math.floor(Math.random() * entries.length)];
            setEntry(randomEntry);
            setFields(randomEntry);
          } else {
            setEntryError("No wine entries found for this file");
            setEntry(null);
          }
        })
        .catch((err) => {
          setEntryError(err.message || "Failed to load entries");
          setEntry(null);
        })
        .finally(() => setEntryLoading(false));
    }
  }, [fileId, session?.access_token]);

  useEffect(() => {
    if (roleChecked && user && session?.access_token) {
      fetchRandomEntry();
    }
  }, [fetchRandomEntry, roleChecked, user, session]);

  // Handlers for field changes
  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFields({ ...fields, [e.target.name]: e.target.value });
  };

  // Note: AI and LWIN refinement endpoints are not yet implemented
  const handleRefineAI = () => {
    setEntryError("AI refinement is not yet implemented");
  };

  const handleRefineLWIN = () => {
    setEntryError("LWIN refinement is not yet implemented");
  };

  // Save manual changes
  const handleSave = () => {
    if (!entry || !session?.access_token) return;
    setEntryLoading(true);
    setEntryError(null);
    
    // Map form fields to API fields
    const updateData = {
      producer: fields.producer || null,
      cuvee: fields.cuvee || null,
      type: fields.type || null,
      vintage: fields.vintage || null,
      price: fields.price || null,
      bottle_size: fields.bottle_size || null,
      grape_variety: fields.grape_variety || null,
      country: fields.country || null,
      region: fields.region || null,
      subregion: fields.subregion || null,
      designation: fields.designation || null,
      classification: fields.classification || null,
      sub_type: fields.sub_type || null,
      raw_text: fields.raw_text || null,
      status: 'user_edited' as const
    };
    
    api.updateWineEntry(session.access_token, entry.id, updateData)
      .then(() => {
        fetchRandomEntry();
      })
      .catch((err) => {
        setEntryError(err.message || "Save failed");
      })
      .finally(() => setEntryLoading(false));
  };

  // Next entry
  const handleNext = () => {
    fetchRandomEntry();
  };

  if (loading || !roleChecked) return <div className="p-8">Loading...</div>;
  if (!user || !session) return null;
  if (entryLoading) return <div className="p-8">Loading entry...</div>;
  if (entryError) return <div className="p-8 text-red-500">{entryError}</div>;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold">Refine Wine Entry</h1>
            <button 
              type="button" 
              className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              onClick={() => router.push('/admin/wine-lists')}
            >
              Back to Wine Lists
            </button>
          </div>
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