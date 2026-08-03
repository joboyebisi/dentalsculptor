"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { USER_ROLES } from "@/lib/constants";

export default function SettingsPage() {
  const [profile, setProfile] = useState({
    name: "",
    institution: "",
    department: "",
    country: "",
    role: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/api/user/profile")
      .then((r) => r.json())
      .then((d) => setProfile(d.user ?? profile));
  }, []);

  async function saveProfile() {
    setSaving(true);
    await fetch("/api/user/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    });
    setSaving(false);
  }

  return (
    <div className="p-margin-page">
      <h1 className="text-display-lg">Settings</h1>
      <p className="mt-1 text-body-md text-on-surface-variant">Manage your profile and preferences</p>

      <div className="mt-8 max-w-lg space-y-6">
        <Card>
          <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div><Label>Name</Label><Input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} className="mt-1" /></div>
            <div><Label>Institution</Label><Input value={profile.institution} onChange={(e) => setProfile({ ...profile, institution: e.target.value })} className="mt-1" /></div>
            <div><Label>Department</Label><Input value={profile.department} onChange={(e) => setProfile({ ...profile, department: e.target.value })} className="mt-1" /></div>
            <div><Label>Country</Label><Input value={profile.country} onChange={(e) => setProfile({ ...profile, country: e.target.value })} className="mt-1" /></div>
            <div>
              <Label>Role</Label>
              <select
                value={profile.role}
                onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                className="mt-1 flex h-9 w-full rounded-lg border border-border-subtle bg-panel-bg px-3 text-body-md"
              >
                {USER_ROLES.map((r) => (<option key={r.value} value={r.value}>{r.label}</option>))}
              </select>
            </div>
            <Button onClick={saveProfile} disabled={saving}>{saving ? "Saving..." : "Save Changes"}</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
