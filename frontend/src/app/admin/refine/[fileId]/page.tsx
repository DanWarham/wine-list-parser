"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import axios from "axios";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import { useAuth } from "@/src/supabase-auth-context";
import { api } from "@/utils/api_v2";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

type ViewMode = 'manual' | 'table';

export default function RefinePage() {
  const { fileId } = useParams();
  const router = useRouter();
  const { user, loading, session } = useAuth();
  const [entry, setEntry] = useState<any>(null);
  const [entries, setEntries] = useState<any[]>([]);
  const [entryLoading, setEntryLoading] = useState(false);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [fields, setFields] = useState<any>({});
  const [roleChecked, setRoleChecked] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('manual');
  const [selectedEntries, setSelectedEntries] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

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

  // Fetch all entries
  const fetchEntries = useCallback(() => {
    if (session?.access_token) {
      setEntryLoading(true);
      setEntryError(null);
      api.getWineEntries(session.access_token, fileId as string)
        .then((entries) => {
          setEntries(entries);
          if (entries.length > 0 && viewMode === 'manual') {
            // Pick a random entry for manual view
            const randomEntry = entries[Math.floor(Math.random() * entries.length)];
            setEntry(randomEntry);
            setFields(randomEntry);
          }
        })
        .catch((err) => {
          setEntryError(err.message || "Failed to load entries");
          setEntry(null);
        })
        .finally(() => setEntryLoading(false));
    }
  }, [fileId, session?.access_token, viewMode]);

  useEffect(() => {
    if (roleChecked && user && session?.access_token) {
      fetchEntries();
    }
  }, [fetchEntries, roleChecked, user, session]);

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
        fetchEntries();
      })
      .catch((err) => {
        setEntryError(err.message || "Save failed");
      })
      .finally(() => setEntryLoading(false));
  };

  // Next entry
  const handleNext = () => {
    if (entries.length > 0) {
      const randomEntry = entries[Math.floor(Math.random() * entries.length)];
      setEntry(randomEntry);
      setFields(randomEntry);
    }
  };

  // Table view handlers
  const handleEntrySelect = (entryId: string, checked: boolean) => {
    const newSelected = new Set(selectedEntries);
    if (checked) {
      newSelected.add(entryId);
    } else {
      newSelected.delete(entryId);
    }
    setSelectedEntries(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedEntries(new Set(filteredEntries.map(e => e.id)));
    } else {
      setSelectedEntries(new Set());
    }
  };

  const handleBulkUpdate = async (field: string, value: string) => {
    if (selectedEntries.size === 0 || !session?.access_token) return;
    
    setEntryLoading(true);
    setEntryError(null);
    
    try {
      const updates = Array.from(selectedEntries).map(id => ({
        id,
        [field]: value,
        status: 'user_edited' as const
      }));
      
      await api.bulkUpdateWineEntries(session.access_token, updates);
      fetchEntries();
      setSelectedEntries(new Set());
    } catch (err: any) {
      setEntryError(err.message || "Bulk update failed");
    } finally {
      setEntryLoading(false);
    }
  };

  const handleEditEntry = (entry: any) => {
    setEntry(entry);
    setFields(entry);
    setViewMode('manual');
  };

  // Filter entries
  const filteredEntries = entries.filter(entry => {
    const matchesSearch = !searchTerm || 
      entry.raw_text?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.producer?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.cuvee?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || entry.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

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
            <h1 className="text-2xl font-bold">Refine Wine Entries</h1>
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'manual' ? 'default' : 'outline'}
                onClick={() => setViewMode('manual')}
              >
                Manual Refinement
              </Button>
              <Button
                variant={viewMode === 'table' ? 'default' : 'outline'}
                onClick={() => setViewMode('table')}
              >
                Table View
              </Button>
              <Button 
                variant="outline"
                onClick={() => router.push('/admin/wine-lists')}
              >
                Back to Wine Lists
              </Button>
            </div>
          </div>

          {viewMode === 'manual' && entry && (
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
                <Button variant="outline" onClick={handleRefineAI}>Refine with AI</Button>
                <Button variant="outline" onClick={handleRefineLWIN}>Match to LWIN</Button>
                <Button onClick={handleSave}>Save</Button>
                <Button variant="outline" onClick={handleNext}>Next</Button>
              </div>
            </form>
          )}

          {viewMode === 'table' && (
            <div className="space-y-4">
              {/* Search and Filter Controls */}
              <div className="flex gap-4 items-center">
                <Input
                  placeholder="Search entries..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="max-w-sm"
                />
                <Select 
                  value={statusFilter} 
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-[180px]"
                >
                  <option value="all">All Statuses</option>
                  <option value="auto">Auto</option>
                  <option value="user_edited">User Edited</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="rejected">Rejected</option>
                </Select>
              </div>

              {/* Bulk Actions */}
              {selectedEntries.size > 0 && (
                <div className="bg-blue-50 p-4 rounded-lg border">
                  <h3 className="font-semibold mb-2">Bulk Actions ({selectedEntries.size} selected)</h3>
                  <div className="flex gap-2 flex-wrap">
                    {['producer', 'cuvee', 'vintage', 'price', 'grape_variety', 'country', 'region'].map((field) => (
                      <div key={field} className="flex gap-1">
                        <Input
                          placeholder={field.replace('_', ' ')}
                          className="w-32"
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              handleBulkUpdate(field, e.currentTarget.value);
                              e.currentTarget.value = '';
                            }
                          }}
                        />
                        <Button
                          size="sm"
                          onClick={(e) => {
                            const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                            handleBulkUpdate(field, input.value);
                            input.value = '';
                          }}
                        >
                          Set
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Table */}
              <div className="border rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="p-3 text-left">
                          <Checkbox
                            checked={selectedEntries.size === filteredEntries.length && filteredEntries.length > 0}
                            onCheckedChange={(checked) => handleSelectAll(checked as boolean)}
                          />
                        </th>
                        <th className="p-3 text-left">Raw Text</th>
                        <th className="p-3 text-left">Producer</th>
                        <th className="p-3 text-left">Cuvée</th>
                        <th className="p-3 text-left">Vintage</th>
                        <th className="p-3 text-left">Price</th>
                        <th className="p-3 text-left">Status</th>
                        <th className="p-3 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEntries.map((entry) => (
                        <tr key={entry.id} className="border-t hover:bg-gray-50">
                          <td className="p-3">
                            <Checkbox
                              checked={selectedEntries.has(entry.id)}
                              onCheckedChange={(checked) => handleEntrySelect(entry.id, checked as boolean)}
                            />
                          </td>
                          <td className="p-3 text-sm max-w-xs truncate">
                            {entry.raw_text}
                          </td>
                          <td className="p-3 text-sm">{entry.producer}</td>
                          <td className="p-3 text-sm">{entry.cuvee}</td>
                          <td className="p-3 text-sm">{entry.vintage}</td>
                          <td className="p-3 text-sm">{entry.price}</td>
                          <td className="p-3 text-sm">
                            <span className={`px-2 py-1 rounded text-xs ${
                              entry.status === 'auto' ? 'bg-gray-100' :
                              entry.status === 'user_edited' ? 'bg-blue-100' :
                              entry.status === 'confirmed' ? 'bg-green-100' :
                              'bg-red-100'
                            }`}>
                              {entry.status}
                            </span>
                          </td>
                          <td className="p-3">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleEditEntry(entry)}
                            >
                              Edit
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              <div className="text-sm text-gray-600">
                Showing {filteredEntries.length} of {entries.length} entries
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
} 