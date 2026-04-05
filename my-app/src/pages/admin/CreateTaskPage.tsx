import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { MarkdownEditor } from "@/components/ui/markdown-editor";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { useApi } from "@/hooks/useApi";
import { useClassContext } from "@/contexts/ClassContext";
import { tasksApi } from "@/api/tasks";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";
import {
  PlusCircle,
  Loader2,
  Trash2,
  ClipboardList,
  X,
  Send,
  Plus,
} from "lucide-react";
import type { Task, LearningResource } from "@/types/task";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fieldFilledCount(draft: Task): number {
  let count = 0;
  if (draft.title.trim()) count++;
  if (draft.description.trim()) count++;
  if (draft.grading_criteria.trim()) count++;
  return count;
}

function progressVariant(count: number): "secondary" | "outline" | "default" {
  if (count >= 3) return "default";
  if (count >= 2) return "outline";
  return "secondary";
}

interface FormValues {
  title: string;
  description: string;
  criteria: string;
}

const EMPTY_FORM: FormValues = { title: "", description: "", criteria: "" };

function formFromDraft(draft: Task): FormValues {
  return {
    title: draft.title,
    description: draft.description,
    criteria: draft.grading_criteria,
  };
}

function formEquals(a: FormValues, b: FormValues): boolean {
  return (
    a.title === b.title &&
    a.description === b.description &&
    a.criteria === b.criteria
  );
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function CreateTaskPage() {
  const navigate = useNavigate();
  const { classes, currentClass } = useClassContext();

  const {
    data: draftsData,
    loading,
    error,
    refetch,
  } = useApi(() => tasksApi.list("draft"), []);

  // Sheet state
  const [sheetOpen, setSheetOpen] = useState(false);
  const [selectedDraft, setSelectedDraft] = useState<Task | null>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState("");
  const initialValuesRef = useRef<FormValues>(EMPTY_FORM);

  // Learning resources state (independent from FormValues — not a publish requirement)
  const [learningResources, setLearningResources] = useState<LearningResource[]>([]);
  const initialResourcesRef = useRef<LearningResource[]>([]);
  const [showAddResource, setShowAddResource] = useState(false);
  const [newResourceUrl, setNewResourceUrl] = useState("");
  const [newResourceTitle, setNewResourceTitle] = useState("");

  // Async operation state
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Dialog state
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);

  // Batch publish state
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [selectedClassIds, setSelectedClassIds] = useState<string[]>([]);
  const [batchPublishing, setBatchPublishing] = useState(false);

  const drafts = draftsData?.items ?? [];

  // Derived values
  const currentForm: FormValues = { title, description, criteria };
  const isDirty =
    !formEquals(currentForm, initialValuesRef.current) ||
    JSON.stringify(learningResources) !== JSON.stringify(initialResourcesRef.current);
  const canSave = title.trim().length > 0 && isDirty;
  const canPublish =
    title.trim().length > 0 &&
    description.trim().length > 0 &&
    criteria.trim().length > 0;

  if (classes.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-12 w-12" />}
        title="请先创建班级"
        description="需要至少一个班级才能发布作业"
        action={
          <Button onClick={() => navigate("/admin/classes")}>
            <PlusCircle className="mr-2 h-4 w-4" />
            前往班级管理
          </Button>
        }
      />
    );
  }

  // ------- Sheet open/close -------

  function openSheetForNew() {
    setSelectedDraft(null);
    setTitle("");
    setDescription("");
    setCriteria("");
    initialValuesRef.current = EMPTY_FORM;
    setLearningResources([]);
    initialResourcesRef.current = [];
    setShowAddResource(false);
    setSheetOpen(true);
  }

  function openSheetForEdit(draft: Task) {
    setSelectedDraft(draft);
    const vals = formFromDraft(draft);
    setTitle(vals.title);
    setDescription(vals.description);
    setCriteria(vals.criteria);
    initialValuesRef.current = vals;
    const resources = draft.learning_resources ?? [];
    setLearningResources(resources);
    initialResourcesRef.current = resources;
    setShowAddResource(false);
    setSheetOpen(true);
  }

  function requestClose() {
    if (isDirty) {
      setShowDiscardDialog(true);
    } else {
      setSheetOpen(false);
    }
  }

  function handleDiscard() {
    setShowDiscardDialog(false);
    setSheetOpen(false);
  }

  const handleSheetOpenChange = useCallback(
    (open: boolean) => {
      if (!open) {
        const current: FormValues = { title, description, criteria };
        if (!formEquals(current, initialValuesRef.current)) {
          setShowDiscardDialog(true);
        } else {
          setSheetOpen(false);
        }
      } else {
        setSheetOpen(true);
      }
    },
    [title, description, criteria],
  );

  // ------- Save draft -------

  async function handleSave() {
    if (!canSave) return;
    const draftClassId = selectedDraft?.class_id ?? classes[0]?.id;
    if (!draftClassId) return;
    setSaving(true);
    try {
      const resourcesPayload = learningResources.length > 0 ? learningResources : null;
      if (selectedDraft) {
        const updated = await tasksApi.update(selectedDraft.id, {
          title: title.trim(),
          description: description,
          grading_criteria: criteria,
          learning_resources: resourcesPayload,
        });
        setSelectedDraft(updated);
        initialValuesRef.current = formFromDraft(updated);
        initialResourcesRef.current = updated.learning_resources ?? [];
      } else {
        const created = await tasksApi.create({
          title: title.trim(),
          description: description,
          grading_criteria: criteria,
          learning_resources: resourcesPayload,
          class_id: draftClassId,
        });
        setSelectedDraft(created);
        initialValuesRef.current = formFromDraft(created);
        initialResourcesRef.current = created.learning_resources ?? [];
      }
      toast.success("草稿已保存");
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  // ------- Publish (select classes) -------

  function openPublish() {
    const defaultId = currentClass?.id ?? classes[0]?.id;
    setSelectedClassIds(defaultId ? [defaultId] : []);
    setShowBatchDialog(true);
  }

  async function handleBatchPublish() {
    if (!canPublish || selectedClassIds.length === 0) return;
    setBatchPublishing(true);
    try {
      const res = await tasksApi.batchPublish({
        title: title.trim(),
        description: description,
        grading_criteria: criteria,
        learning_resources: learningResources.length > 0 ? learningResources : null,
        class_ids: selectedClassIds,
        status: "published",
      });
      toast.success(`已发布到 ${res.created.length} 个班级的作业列表`);
      setShowBatchDialog(false);
      initialValuesRef.current = { title: title.trim(), description, criteria };
      setSheetOpen(false);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "发布失败");
    } finally {
      setBatchPublishing(false);
    }
  }

  // ------- AI Generate -------

  async function handleGenerate() {
    if (!title.trim() || !description.trim()) return;

    if (
      criteria.trim() &&
      !window.confirm("当前打分标准内容将被覆盖，是否继续？")
    ) {
      return;
    }

    setGenerating(true);
    try {
      const result = await tasksApi.generateCriteria({
        title: title.trim(),
        description: description.trim(),
      });
      setCriteria(result.criteria);
      toast.success("打分标准已生成");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  // ------- Delete -------

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await tasksApi.delete(deleteTarget.id);
      toast.success("草稿已删除");
      if (selectedDraft?.id === deleteTarget.id) {
        initialValuesRef.current = EMPTY_FORM;
        setSheetOpen(false);
      }
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  // ------- Loading / Error -------

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-28" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  // ------- Render -------

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold page-title-decorated">作业草稿（待发布）</h1>
        <Button onClick={openSheetForNew}>
          <PlusCircle className="mr-2 h-4 w-4" />
          新建草稿
        </Button>
      </div>

      {drafts.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-12 w-12" />}
          title="暂无草稿"
          description="点击右上角「新建草稿」开始创建"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {drafts.map((draft, index) => {
            const filled = fieldFilledCount(draft);
            return (
              <Card
                key={draft.id}
                className="group relative cursor-pointer card-scroll animate-scroll-reveal rounded-xl border-[var(--paper-border)]"
                style={{ "--stagger-index": index } as React.CSSProperties}
                onClick={() => openSheetForEdit(draft)}
              >
                <CardContent className="py-4">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-base font-medium leading-snug line-clamp-2">
                      {draft.title}
                    </h3>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(draft);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {formatDate(draft.created_at, { hour: "2-digit", minute: "2-digit" })}
                  </p>
                  <Badge variant={progressVariant(filled)} className="mt-2">
                    {filled}/3 已填写
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Sheet editor */}
      <Sheet open={sheetOpen} onOpenChange={handleSheetOpenChange}>
        <SheetContent
          side="right"
          showCloseButton={false}
          className="sm:max-w-[75vw] overflow-y-auto"
        >
          <SheetHeader>
            <div className="flex items-center justify-between">
              <div>
                <SheetTitle>
                  {selectedDraft ? "编辑草稿" : "新建草稿"}
                </SheetTitle>
                <SheetDescription>
                  {selectedDraft
                    ? "修改草稿内容，完善后可发布"
                    : "填写任务信息，至少需要标题"}
                </SheetDescription>
              </div>
              <Button variant="ghost" size="icon-sm" onClick={requestClose}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </SheetHeader>

          <div className="flex-1 space-y-4 px-4">
            <div className="space-y-2">
              <Label htmlFor="draft-title">
                标题 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="draft-title"
                placeholder="请输入任务标题"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="draft-description">任务说明</Label>
              <Textarea
                id="draft-description"
                placeholder="请输入任务说明"
                rows={5}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>打分标准</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!title.trim() || !description.trim() || generating}
                  onClick={handleGenerate}
                >
                  {generating && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  AI 生成
                </Button>
              </div>
              <MarkdownEditor
                value={criteria}
                onChange={setCriteria}
                placeholder="请输入打分标准"
              />
              <p className="text-xs text-muted-foreground">
                此标准将作为 AI 批改的依据
              </p>
            </div>

            {/* Learning resources */}
            <div className="space-y-2">
              <Label>学习资源</Label>
              {learningResources.length > 0 ? (
                <div className="space-y-2">
                  {learningResources.map((resource, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-2 rounded-md border border-[var(--paper-border)] p-3"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{resource.title}</p>
                        <a
                          href={resource.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[var(--cyan-light)] hover:underline truncate block"
                        >
                          {resource.url}
                        </a>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="shrink-0"
                        onClick={() =>
                          setLearningResources((prev) => prev.filter((_, i) => i !== index))
                        }
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-2">
                  暂无学习资源。可通过 AI 助教设计作业时自动添加，或手动添加。
                </p>
              )}
              {showAddResource ? (
                <div className="space-y-2 rounded-md border border-[var(--paper-border)] p-3">
                  <Input
                    placeholder="URL"
                    value={newResourceUrl}
                    onChange={(e) => setNewResourceUrl(e.target.value)}
                  />
                  <Input
                    placeholder="标题"
                    value={newResourceTitle}
                    onChange={(e) => setNewResourceTitle(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      disabled={!newResourceUrl.trim() || !newResourceTitle.trim() || !/^https?:\/\//i.test(newResourceUrl.trim())}
                      onClick={() => {
                        setLearningResources((prev) => [
                          ...prev,
                          { url: newResourceUrl.trim(), title: newResourceTitle.trim(), content: "" },
                        ]);
                        setNewResourceUrl("");
                        setNewResourceTitle("");
                        setShowAddResource(false);
                      }}
                    >
                      添加
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setNewResourceUrl("");
                        setNewResourceTitle("");
                        setShowAddResource(false);
                      }}
                    >
                      取消
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAddResource(true)}
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  添加资源
                </Button>
              )}
            </div>
          </div>

          <SheetFooter className="flex-row justify-between border-t pt-4">
            <Button
              variant="outline"
              disabled={!canSave || saving}
              onClick={handleSave}
            >
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存草稿
            </Button>
            <Button
              disabled={!canPublish}
              onClick={openPublish}
            >
              <Send className="mr-2 h-4 w-4" />
              发布
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Publish dialog */}
      <Dialog open={showBatchDialog} onOpenChange={setShowBatchDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>选择发布班级</DialogTitle>
            <DialogDescription>
              每个班级将生成独立的作业记录
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            <label className="flex items-center gap-2 py-1.5 px-1 cursor-pointer border-b border-[var(--paper-border)] mb-1">
              <Checkbox
                checked={selectedClassIds.length === classes.length}
                onCheckedChange={(checked) =>
                  setSelectedClassIds(checked ? classes.map((c) => c.id) : [])
                }
              />
              <span className="text-sm font-medium">全选</span>
            </label>
            {classes.map((c) => (
              <label key={c.id} className="flex items-center gap-2 py-1.5 px-1 cursor-pointer">
                <Checkbox
                  checked={selectedClassIds.includes(c.id)}
                  onCheckedChange={(checked) => {
                    setSelectedClassIds((prev) =>
                      checked ? [...prev, c.id] : prev.filter((id) => id !== c.id)
                    );
                  }}
                />
                <span className="text-sm">{c.name}</span>
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBatchDialog(false)}>
              取消
            </Button>
            <Button
              disabled={selectedClassIds.length === 0 || batchPublishing}
              onClick={handleBatchPublish}
            >
              {batchPublishing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              发布到 {selectedClassIds.length} 个班级
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Discard dialog */}
      <Dialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>放弃修改？</DialogTitle>
            <DialogDescription>
              有未保存的修改，关闭后将丢失这些内容。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDiscardDialog(false)}
            >
              取消
            </Button>
            <Button variant="destructive" onClick={handleDiscard}>
              放弃
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除草稿"
        description={`确定要删除草稿「${deleteTarget?.title}」吗？此操作不可撤销。`}
        confirmText="删除"
        onConfirm={handleDelete}
        loading={deleting}
      />
    </div>
  );
}
