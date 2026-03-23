import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { tasksApi } from "@/api/tasks";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function CreateTaskPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const isValid = title.trim() && description.trim() && criteria.trim();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await tasksApi.create({
        title: title.trim(),
        description: description.trim(),
        grading_criteria: criteria.trim(),
      });
      toast.success("任务发布成功");
      navigate("/admin/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "发布失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-semibold">发布任务</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">任务信息</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">标题</Label>
              <Input
                id="title"
                placeholder="请输入任务标题"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">任务说明</Label>
              <Textarea
                id="description"
                placeholder="请输入任务说明"
                rows={6}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="criteria">打分标准</Label>
              <Textarea
                id="criteria"
                placeholder="请输入打分标准"
                rows={6}
                value={criteria}
                onChange={(e) => setCriteria(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">此标准将作为 AI 批改的依据</p>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={!isValid || loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              发布任务
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
