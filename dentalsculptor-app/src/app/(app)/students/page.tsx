"use client";

import { useState, useEffect } from "react";
import { Play, CheckCircle, Clock, MessageSquare } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Link from "next/link";
import { useResearchTracker } from "@/hooks/use-research-tracker";

interface Assignment {
  id: string;
  status: string;
  score: number | null;
  reflection: string | null;
  feedback: string | null;
  project: { id: string; title: string; description: string | null };
}

export default function StudentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [reflection, setReflection] = useState("");
  const [selectedAssignment, setSelectedAssignment] = useState<string | null>(null);
  const { track } = useResearchTracker();

  useEffect(() => {
    fetch("/api/students/assignments")
      .then((r) => r.json())
      .then((d) => setAssignments(d.assignments ?? []));
  }, []);

  async function submitReflection(assignmentId: string) {
    await fetch(`/api/students/assignments/${assignmentId}/reflection`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reflection }),
    });
    track("REFLECTION_SUBMITTED", undefined, { assignmentId });
    setReflection("");
    setSelectedAssignment(null);
  }

  const completed = assignments.filter((a) => a.status === "COMPLETED" || a.status === "SUBMITTED");
  const inProgress = assignments.filter((a) => a.status === "IN_PROGRESS");
  const assigned = assignments.filter((a) => a.status === "ASSIGNED");

  return (
    <div className="p-margin-page">
      <h1 className="text-display-lg">Student Portal</h1>
      <p className="mt-1 text-body-md text-on-surface-variant">
        Access simulations, complete activities, and submit reflections
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="flex items-center gap-4 p-4"><Clock className="h-8 w-8 text-warning" /><div><p className="text-2xl font-bold">{assigned.length}</p><p className="text-body-sm text-on-surface-variant">Assigned</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-4 p-4"><Play className="h-8 w-8 text-primary-container" /><div><p className="text-2xl font-bold">{inProgress.length}</p><p className="text-body-sm text-on-surface-variant">In Progress</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-4 p-4"><CheckCircle className="h-8 w-8 text-secondary" /><div><p className="text-2xl font-bold">{completed.length}</p><p className="text-body-sm text-on-surface-variant">Completed</p></div></CardContent></Card>
      </div>

      <Tabs defaultValue="assignments" className="mt-8">
        <TabsList>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
          <TabsTrigger value="progress">Progress</TabsTrigger>
          <TabsTrigger value="scores">Scores</TabsTrigger>
        </TabsList>
        <TabsContent value="assignments" className="mt-4 space-y-4">
          {assignments.length === 0 ? (
            <Card className="py-12 text-center"><CardContent><p className="text-on-surface-variant">No assignments yet</p></CardContent></Card>
          ) : (
            assignments.map((a) => (
              <Card key={a.id}>
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <h3 className="font-semibold">{a.project.title}</h3>
                    <p className="text-body-sm text-on-surface-variant">{a.project.description}</p>
                    <Badge variant="outline" className="mt-2">{a.status}</Badge>
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/editor/${a.project.id}`}>
                      <Button size="sm" onClick={() => track("ASSIGNMENT_STARTED", a.project.id)}>
                        <Play className="mr-1 h-4 w-4" />Launch
                      </Button>
                    </Link>
                    <Button size="sm" variant="outline" onClick={() => setSelectedAssignment(a.id)}>
                      <MessageSquare className="mr-1 h-4 w-4" />Reflect
                    </Button>
                  </div>
                </CardContent>
                {selectedAssignment === a.id && (
                  <CardContent className="border-t border-border-subtle pt-4">
                    <Label>Submit Reflection</Label>
                    <Textarea value={reflection} onChange={(e) => setReflection(e.target.value)} className="mt-2" rows={4} placeholder="Share your learning experience..." />
                    <Button className="mt-2" size="sm" onClick={() => submitReflection(a.id)}>Submit</Button>
                  </CardContent>
                )}
              </Card>
            ))
          )}
        </TabsContent>
        <TabsContent value="progress">
          <Card><CardContent className="p-6"><p className="text-on-surface-variant">Track your learning progress across all assigned simulations.</p></CardContent></Card>
        </TabsContent>
        <TabsContent value="scores">
          <Card><CardContent className="p-6">
            {completed.map((a) => (
              <div key={a.id} className="flex justify-between border-b border-border-subtle py-3 last:border-0">
                <span>{a.project.title}</span>
                <span className="font-semibold">{a.score ?? "Pending"}</span>
              </div>
            ))}
          </CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
