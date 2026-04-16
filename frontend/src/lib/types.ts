export type UserRole = "student" | "admin";

export interface AuthUser {
  id: number;
  email: string;
  role: UserRole;
  fullName: string;
  gradeLabel: string | null;
  initials: string;
  avatarUrl: string | null;
}

export interface Session {
  token: string;
  user: AuthUser;
}

export interface TaskItem {
  id: number;
  title: string;
  description: string;
  prompt: string;
  answer: string;
  gradeLevel: string;
  category: string;
  difficulty: string;
  status: string;
  imageUrl: string | null;
  estimatedMinutes: number;
  badge: string | null;
  badgeTone: string;
  questionType: "numeric" | "choice";
  choices: string[];
  updatedAt: string;
  completed?: boolean;
  lastScore?: number | null;
  attemptCount?: number;
}

export interface StudentDashboardPayload {
  user: AuthUser;
  summary: {
    activeTasks: number;
    completedTasks: number;
    pendingTasks: number;
    averageScore: number;
  };
  nextTask: TaskItem | null;
  recentResults: Array<{
    taskId: number;
    taskTitle: string;
    score: number;
    submittedAt: string;
    isCorrect: boolean;
  }>;
  tests: TaskItem[];
}

export interface StudentTestPayload {
  user: AuthUser;
  task: TaskItem;
  meta: {
    questionNumber: number;
    totalQuestions: number;
    timeRemaining: string;
    progressPercent: number;
    hintText: string;
  };
  lastSubmission: {
    answer: string;
    score: number;
    isCorrect: boolean;
  } | null;
}

export interface SubmissionResponse {
  taskId: number;
  submittedAnswer: string;
  expectedAnswer: string;
  isCorrect: boolean;
  score: number;
  message: string;
}

export interface AdminDashboardPayload {
  user: AuthUser;
  metrics: {
    activeStudents: number;
    totalTests: number;
    activeTasks: number;
    draftTasks: number;
    totalSubmissions: number;
    averageScore: number;
  };
  recentResults: Array<{
    studentName: string;
    taskTitle: string;
    score: number;
    timeLabel: string;
  }>;
  recentTasks: Array<{
    id: number;
    title: string;
    gradeLevel: string;
    category: string;
    status: string;
    updatedAt: string;
  }>;
}

export interface TaskListPayload {
  items: TaskItem[];
  summary: {
    total: number;
    active: number;
    drafts: number;
  };
}
