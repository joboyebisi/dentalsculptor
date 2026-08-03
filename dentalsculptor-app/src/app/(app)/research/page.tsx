"use client";

import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Download, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LIKERT_QUESTIONS } from "@/lib/constants";

interface Metrics {
  ownershipScore: number;
  agencyScore: number;
  personalisationScore: number;
  confidenceScore: number;
  projectsCreated: number;
  modelsGenerated: number;
  aiAccepted: number;
  aiRejected: number;
  aiAcceptRate: number;
  annotations: number;
  published: number;
  totalEvents: number;
}

interface TimelineEvent {
  id: string;
  eventType: string;
  timestamp: string;
  user: { name: string | null };
  project: { title: string } | null;
}

const COLORS = ["#0F3D91", "#7C3AED", "#4F46E5", "#14B8A6"];

export default function ResearchDashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [surveyResponses, setSurveyResponses] = useState<Array<{ question: string; avg: number }>>([]);
  const [likertValues, setLikertValues] = useState<Record<string, number>>({});

  useEffect(() => {
    fetch("/api/research/metrics").then((r) => r.json()).then((d) => setMetrics(d.metrics));
    fetch("/api/research/timeline").then((r) => r.json()).then((d) => setTimeline(d.events ?? []));
    fetch("/api/research/surveys").then((r) => r.json()).then((d) => setSurveyResponses(d.summary ?? []));
  }, []);

  async function exportData(format: string) {
    const res = await fetch(`/api/research/export?format=${format}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dentalsculptor-research.${format.toLowerCase()}`;
    a.click();
  }

  async function submitSurvey() {
    for (const [question, scale] of Object.entries(likertValues)) {
      await fetch("/api/research/surveys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, answer: String(scale), scale }),
      });
    }
    alert("Survey submitted. Thank you for your participation.");
  }

  const ownershipData = metrics
    ? [
        { name: "Ownership", value: metrics.ownershipScore },
        { name: "Agency", value: metrics.agencyScore },
        { name: "Personalisation", value: metrics.personalisationScore },
        { name: "Confidence", value: metrics.confidenceScore },
      ]
    : [];

  const aiData = metrics
    ? [
        { name: "Accepted", value: metrics.aiAccepted },
        { name: "Rejected", value: metrics.aiRejected },
      ]
    : [];

  const activityData = timeline.slice(0, 20).map((e) => ({
    time: new Date(e.timestamp).toLocaleTimeString(),
    event: e.eventType.replace(/_/g, " ").slice(0, 15),
  }));

  return (
    <div className="p-margin-page">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <Badge variant="research" className="mb-2"><Shield className="mr-1 inline h-3 w-3" />Research Access</Badge>
          <h1 className="text-display-lg">Research Dashboard</h1>
          <p className="mt-1 text-body-md text-on-surface-variant">Doctoral research evidence collection and analysis</p>
        </div>
        <div className="flex gap-2">
          {["CSV", "JSON", "XLSX"].map((fmt) => (
            <Button key={fmt} variant="outline" size="sm" onClick={() => exportData(fmt)}>
              <Download className="mr-1 h-4 w-4" />{fmt}
            </Button>
          ))}
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="ai">AI Analytics</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="survey">Survey Engine</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {ownershipData.map((item) => (
              <Card key={item.name}>
                <CardContent className="p-6 text-center">
                  <p className="text-3xl font-bold text-research-indigo">{item.value}</p>
                  <p className="text-body-sm text-on-surface-variant">{item.name} Score</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Authoring Behaviour</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div><p className="text-2xl font-bold">{metrics?.projectsCreated ?? 0}</p><p className="text-body-sm text-on-surface-variant">Projects Created</p></div>
                  <div><p className="text-2xl font-bold">{metrics?.modelsGenerated ?? 0}</p><p className="text-body-sm text-on-surface-variant">Models Generated</p></div>
                  <div><p className="text-2xl font-bold">{metrics?.annotations ?? 0}</p><p className="text-body-sm text-on-surface-variant">Annotations</p></div>
                  <div><p className="text-2xl font-bold">{metrics?.published ?? 0}</p><p className="text-body-sm text-on-surface-variant">Published</p></div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Pedagogical Ownership</CardTitle></CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ownershipData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="ai" className="mt-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>AI Interaction Analytics</CardTitle></CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={aiData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                      {aiData.map((_, i) => (<Cell key={i} fill={COLORS[i % COLORS.length]} />))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <p className="text-3xl font-bold text-ai-purple">{metrics?.aiAcceptRate ?? 0}%</p>
                <p className="text-body-sm text-on-surface-variant">AI Suggestion Accept Rate</p>
                <div className="mt-6 space-y-3">
                  <div className="flex justify-between"><span>Suggestions Accepted</span><span className="font-semibold">{metrics?.aiAccepted ?? 0}</span></div>
                  <div className="flex justify-between"><span>Suggestions Rejected</span><span className="font-semibold">{metrics?.aiRejected ?? 0}</span></div>
                  <div className="flex justify-between"><span>Total AI Events</span><span className="font-semibold">{(metrics?.aiAccepted ?? 0) + (metrics?.aiRejected ?? 0)}</span></div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="activity" className="mt-6">
          <Card>
            <CardHeader><CardTitle>Activity Timeline</CardTitle></CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={activityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                  <YAxis hide />
                  <Tooltip />
                  <Line type="monotone" dataKey="event" stroke="#0F3D91" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card className="mt-4">
            <CardContent className="max-h-64 overflow-y-auto p-4">
              {timeline.map((e) => (
                <div key={e.id} className="flex justify-between border-b border-border-subtle py-2 text-body-sm last:border-0">
                  <span>{e.eventType.replace(/_/g, " ")}</span>
                  <span className="text-on-surface-variant">{e.user.name} · {new Date(e.timestamp).toLocaleString()}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="survey" className="mt-6">
          <Card>
            <CardHeader><CardTitle>Likert Scale Survey</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              {LIKERT_QUESTIONS.map((question) => (
                <div key={question}>
                  <p className="mb-2 text-body-sm font-medium">{question}</p>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        onClick={() => setLikertValues((prev) => ({ ...prev, [question]: n }))}
                        className={`h-10 w-10 rounded-lg border text-sm font-medium transition-colors ${
                          likertValues[question] === n
                            ? "border-research-indigo bg-research-indigo text-white"
                            : "border-border-subtle hover:bg-surface-container"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                  <div className="mt-1 flex justify-between text-xs text-on-surface-variant">
                    <span>Strongly Disagree</span><span>Strongly Agree</span>
                  </div>
                </div>
              ))}
              <Button variant="research" onClick={submitSurvey}>Submit Survey Responses</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
