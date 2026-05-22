#include <cstdlib>
#include <cerrno>
#include <csignal>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifdef _WIN32
#include <process.h>
#include <windows.h>
#else
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;

namespace {

#ifndef _WIN32
volatile sig_atomic_t g_child_process_group = 0;

extern "C" void forward_signal_to_child_process_group(int signal_number)
{
    const int saved_errno = errno;
    const pid_t child_process_group =
        static_cast<pid_t>(g_child_process_group);
    if (child_process_group > 0) {
        kill(child_process_group, signal_number);
        kill(-child_process_group, signal_number);
    }
    errno = saved_errno;
}

struct SignalForwardingGuard {
    struct sigaction previous_sigint {};
    struct sigaction previous_sigterm {};
    bool sigint_installed = false;
    bool sigterm_installed = false;

    SignalForwardingGuard()
    {
        install(SIGINT, previous_sigint, sigint_installed);
        install(SIGTERM, previous_sigterm, sigterm_installed);
    }

    ~SignalForwardingGuard()
    {
        restore(SIGINT, previous_sigint, sigint_installed);
        restore(SIGTERM, previous_sigterm, sigterm_installed);
        g_child_process_group = 0;
    }

    void install(
        int signal_number,
        struct sigaction &previous_action,
        bool &installed)
    {
        struct sigaction action {};
        action.sa_handler = forward_signal_to_child_process_group;
        sigemptyset(&action.sa_mask);
        action.sa_flags = 0;
        if (sigaction(signal_number, &action, &previous_action) == 0) {
            installed = true;
        }
    }

    void restore(
        int signal_number,
        const struct sigaction &previous_action,
        bool installed)
    {
        if (!installed) {
            return;
        }
        sigaction(signal_number, &previous_action, nullptr);
    }
};
#endif

struct CliOptions {
    std::string mode = "auto";
    std::optional<fs::path> manifest_path;
    std::optional<fs::path> repo_root;
    std::optional<fs::path> python_executable;
    bool no_fork = false;
    bool print_plan = false;
    bool dry_run = false;
    bool diagnose = false;
    std::vector<std::string> app_args;
};

struct LaunchPlan {
    std::string mode;
    fs::path bundle_root;
    fs::path python_executable;
    std::string entrypoint = "airunner.launcher";
    std::optional<fs::path> manifest_path;
    std::optional<fs::path> repo_root;
    std::optional<fs::path> pythonpath;
    std::optional<fs::path> llama_server_bin;
    std::optional<fs::path> whisper_server_bin;
    std::vector<std::string> app_args;
};

struct ValidationResult {
    std::vector<std::string> errors;
    std::vector<std::string> warnings;

    [[nodiscard]] bool ok() const
    {
        return errors.empty();
    }
};

std::string trim(std::string value)
{
    const auto start = value.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) {
        return "";
    }
    const auto end = value.find_last_not_of(" \t\r\n");
    return value.substr(start, end - start + 1);
}

std::string path_separator()
{
#ifdef _WIN32
    return ";";
#else
    return ":";
#endif
}

std::optional<std::string> getenv_string(const char *name)
{
    const char *value = std::getenv(name);
    if (value == nullptr || *value == '\0') {
        return std::nullopt;
    }
    return std::string(value);
}

fs::path normalized_absolute_path(const fs::path &path)
{
    if (path.is_absolute()) {
        return path.lexically_normal();
    }
    return fs::absolute(path).lexically_normal();
}

fs::path current_executable_path()
{
#ifdef _WIN32
    std::vector<char> buffer(MAX_PATH);
    const DWORD size = GetModuleFileNameA(nullptr, buffer.data(),
        static_cast<DWORD>(buffer.size()));
    if (size == 0) {
        return fs::current_path();
    }
    return fs::path(std::string(buffer.data(), size));
#else
    std::vector<char> buffer(4096);
    const auto size = readlink("/proc/self/exe", buffer.data(), buffer.size());
    if (size <= 0) {
        return fs::current_path();
    }
    return fs::path(std::string(buffer.data(), static_cast<size_t>(size)));
#endif
}

bool looks_like_repo_root(const fs::path &candidate)
{
    return fs::exists(candidate / "setup.py")
        && fs::exists(candidate / "src" / "airunner" / "launcher.py");
}

std::optional<fs::path> find_repo_root(const fs::path &start)
{
    auto current = fs::absolute(start);
    if (!fs::is_directory(current)) {
        current = current.parent_path();
    }

    while (!current.empty()) {
        if (looks_like_repo_root(current)) {
            return current;
        }
        const auto parent = current.parent_path();
        if (parent == current) {
            break;
        }
        current = parent;
    }
    return std::nullopt;
}

std::optional<fs::path> find_dev_python(const fs::path &repo_root)
{
#ifdef _WIN32
    const std::vector<fs::path> candidates = {
        repo_root / "venv" / "Scripts" / "python.exe",
        repo_root / ".venv" / "Scripts" / "python.exe",
    };
#else
    const std::vector<fs::path> candidates = {
        repo_root / "venv" / "bin" / "python",
        repo_root / ".venv" / "bin" / "python",
    };
#endif

    for (const auto &candidate : candidates) {
        if (fs::exists(candidate)) {
            return normalized_absolute_path(candidate);
        }
    }
    return std::nullopt;
}

std::map<std::string, std::string> parse_manifest(const fs::path &manifest_path)
{
    std::ifstream input(manifest_path);
    if (!input) {
        throw std::runtime_error(
            "Unable to open runtime manifest: " + manifest_path.string());
    }

    std::map<std::string, std::string> values;
    std::string line;
    while (std::getline(input, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') {
            continue;
        }

        const auto separator = line.find('=');
        if (separator == std::string::npos) {
            continue;
        }

        auto key = trim(line.substr(0, separator));
        auto value = trim(line.substr(separator + 1));
        if (value.size() >= 2 && value.front() == '"' && value.back() == '"') {
            value = value.substr(1, value.size() - 2);
        }
        if (!key.empty()) {
            values[key] = value;
        }
    }

    return values;
}

std::optional<fs::path> first_existing_path(
    const std::vector<fs::path> &candidates)
{
    for (const auto &candidate : candidates) {
        if (fs::exists(candidate)) {
            return fs::weakly_canonical(candidate);
        }
    }
    return std::nullopt;
}

std::optional<fs::path> default_manifest_path(const fs::path &exe_dir)
{
    return first_existing_path({
        exe_dir / "runtime_manifest.env",
        exe_dir / ".." / "share" / "airunner" / "runtime_manifest.env",
        exe_dir / "share" / "airunner" / "runtime_manifest.env",
    });
}

fs::path resolve_manifest_path(
    const std::string &raw_value,
    const fs::path &manifest_path)
{
    fs::path candidate(raw_value);
    if (candidate.is_absolute()) {
        return normalized_absolute_path(candidate);
    }
    return normalized_absolute_path(manifest_path.parent_path() / candidate);
}

std::string merge_pythonpath(const std::optional<fs::path> &pythonpath)
{
    if (!pythonpath.has_value()) {
        return getenv_string("PYTHONPATH").value_or("");
    }

    const auto current = getenv_string("PYTHONPATH");
    if (!current.has_value() || current->empty()) {
        return pythonpath->string();
    }
    return pythonpath->string() + path_separator() + *current;
}

[[noreturn]] void fail(const std::string &message)
{
    throw std::runtime_error(message);
}

CliOptions parse_args(int argc, char **argv)
{
    CliOptions options;

    for (int index = 1; index < argc; ++index) {
        const std::string arg = argv[index];
        if (arg == "--") {
            for (++index; index < argc; ++index) {
                options.app_args.emplace_back(argv[index]);
            }
            return options;
        }
        if (arg == "--mode" && index + 1 < argc) {
            options.mode = argv[++index];
            continue;
        }
        if (arg == "--manifest" && index + 1 < argc) {
            options.manifest_path = fs::path(argv[++index]);
            continue;
        }
        if (arg == "--repo-root" && index + 1 < argc) {
            options.repo_root = fs::path(argv[++index]);
            continue;
        }
        if (arg == "--python" && index + 1 < argc) {
            options.python_executable = fs::path(argv[++index]);
            continue;
        }
        if (arg == "--no-fork") {
            options.no_fork = true;
            continue;
        }
        if (arg == "--print-plan") {
            options.print_plan = true;
            continue;
        }
        if (arg == "--dry-run") {
            options.print_plan = true;
            options.dry_run = true;
            continue;
        }
        if (arg == "--diagnose") {
            options.print_plan = true;
            options.diagnose = true;
            continue;
        }
        if (arg == "--help" || arg == "-h") {
            std::cout
                << "Usage: airunner [launcher-options] [-- app-args]\n\n"
                << "Launcher options:\n"
                << "  --mode auto|dev|prod\n"
                << "  --manifest <path>\n"
                << "  --repo-root <path>\n"
                << "  --python <path>\n"
                << "  --no-fork\n"
                << "  --print-plan\n"
                << "  --dry-run\n"
                << "  --diagnose\n";
            std::exit(0);
        }

        options.app_args.push_back(arg);
    }

    return options;
}

std::string requested_mode(const CliOptions &options)
{
    if (options.mode != "auto") {
        return options.mode;
    }
    if (const auto env_mode = getenv_string("AIRUNNER_LAUNCH_MODE")) {
        return *env_mode;
    }
    return "auto";
}

LaunchPlan resolve_dev_plan(const CliOptions &options, const fs::path &exe_path)
{
    std::optional<fs::path> repo_root;
    if (options.repo_root.has_value()) {
        repo_root = normalized_absolute_path(*options.repo_root);
    } else if (const auto env_root = getenv_string("AIRUNNER_REPO_ROOT")) {
        repo_root = normalized_absolute_path(fs::path(*env_root));
    } else {
        repo_root = find_repo_root(fs::current_path());
        if (!repo_root.has_value()) {
            repo_root = find_repo_root(exe_path.parent_path());
        }
    }

    if (!repo_root.has_value()) {
        fail("Unable to locate AIRunner repository root for dev mode");
    }

    std::optional<fs::path> python_executable;
    if (options.python_executable.has_value()) {
        python_executable = normalized_absolute_path(*options.python_executable);
    } else if (const auto env_python = getenv_string("AIRUNNER_DEV_PYTHON")) {
        python_executable = normalized_absolute_path(fs::path(*env_python));
    } else {
        python_executable = find_dev_python(*repo_root);
    }

    if (!python_executable.has_value() || !fs::exists(*python_executable)) {
        fail("Unable to locate repository venv Python for dev mode");
    }

    LaunchPlan plan;
    plan.mode = "dev";
    plan.bundle_root = *repo_root;
    plan.repo_root = repo_root;
    plan.python_executable = *python_executable;
    plan.pythonpath = *repo_root / "src";
    plan.app_args = options.app_args;
    return plan;
}

LaunchPlan resolve_prod_plan(const CliOptions &options, const fs::path &exe_path)
{
    std::optional<fs::path> manifest_path;
    if (options.manifest_path.has_value()) {
        manifest_path = normalized_absolute_path(*options.manifest_path);
    } else if (const auto env_manifest = getenv_string(
        "AIRUNNER_RUNTIME_MANIFEST")) {
        manifest_path = normalized_absolute_path(fs::path(*env_manifest));
    } else {
        manifest_path = default_manifest_path(exe_path.parent_path());
    }

    if (!manifest_path.has_value()) {
        fail("Unable to locate runtime manifest for prod mode");
    }

    const auto manifest = parse_manifest(*manifest_path);
    const auto python_it = manifest.find("AIRUNNER_PYTHON");
    if (python_it == manifest.end()) {
        fail("AIRUNNER_PYTHON missing from runtime manifest");
    }

    LaunchPlan plan;
    plan.mode = "prod";
    plan.manifest_path = manifest_path;
    plan.python_executable = resolve_manifest_path(
        python_it->second,
        *manifest_path);
    if (!fs::exists(plan.python_executable)) {
        fail("Bundled Python not found: " + plan.python_executable.string());
    }

    const auto bundle_it = manifest.find("AIRUNNER_BUNDLE_ROOT");
    if (bundle_it != manifest.end()) {
        plan.bundle_root = resolve_manifest_path(bundle_it->second, *manifest_path);
    } else {
        plan.bundle_root = manifest_path->parent_path();
    }

    if (const auto entrypoint_it = manifest.find("AIRUNNER_ENTRYPOINT");
        entrypoint_it != manifest.end() && !entrypoint_it->second.empty()) {
        plan.entrypoint = entrypoint_it->second;
    }

    if (const auto pythonpath_it = manifest.find("AIRUNNER_PYTHONPATH");
        pythonpath_it != manifest.end() && !pythonpath_it->second.empty()) {
        plan.pythonpath = resolve_manifest_path(
            pythonpath_it->second,
            *manifest_path);
    }

    if (const auto llama_it = manifest.find("AIRUNNER_LLAMA_SERVER_BIN");
        llama_it != manifest.end() && !llama_it->second.empty()) {
        plan.llama_server_bin = resolve_manifest_path(
            llama_it->second,
            *manifest_path);
    }

    if (const auto whisper_it = manifest.find("AIRUNNER_WHISPER_SERVER_BIN");
        whisper_it != manifest.end() && !whisper_it->second.empty()) {
        plan.whisper_server_bin = resolve_manifest_path(
            whisper_it->second,
            *manifest_path);
    }

    plan.app_args = options.app_args;
    return plan;
}

LaunchPlan resolve_plan(const CliOptions &options)
{
    const auto exe_path = current_executable_path();
    const auto mode = requested_mode(options);

    if (mode == "dev") {
        return resolve_dev_plan(options, exe_path);
    }
    if (mode == "prod") {
        return resolve_prod_plan(options, exe_path);
    }

    try {
        return resolve_dev_plan(options, exe_path);
    } catch (const std::exception &) {
        return resolve_prod_plan(options, exe_path);
    }
}

void print_plan(const LaunchPlan &plan)
{
    std::cout << "mode=" << plan.mode << '\n';
    std::cout << "bundle_root=" << plan.bundle_root << '\n';
    std::cout << "python=" << plan.python_executable << '\n';
    std::cout << "entrypoint=" << plan.entrypoint << '\n';
    if (plan.repo_root.has_value()) {
        std::cout << "repo_root=" << *plan.repo_root << '\n';
    }
    if (plan.manifest_path.has_value()) {
        std::cout << "manifest=" << *plan.manifest_path << '\n';
    }
    if (plan.pythonpath.has_value()) {
        std::cout << "pythonpath=" << *plan.pythonpath << '\n';
    }
    if (plan.llama_server_bin.has_value()) {
        std::cout << "llama_server=" << *plan.llama_server_bin << '\n';
    }
    if (plan.whisper_server_bin.has_value()) {
        std::cout << "whisper_server=" << *plan.whisper_server_bin << '\n';
    }
    if (!plan.app_args.empty()) {
        std::cout << "app_args=";
        for (size_t index = 0; index < plan.app_args.size(); ++index) {
            if (index > 0) {
                std::cout << ' ';
            }
            std::cout << plan.app_args[index];
        }
        std::cout << '\n';
    }
}

ValidationResult validate_plan(const LaunchPlan &plan)
{
    ValidationResult result;

    if (!fs::exists(plan.bundle_root)) {
        result.errors.push_back(
            "bundle root does not exist: " + plan.bundle_root.string());
    }

    if (!fs::exists(plan.python_executable)) {
        result.errors.push_back(
            "python executable does not exist: "
            + plan.python_executable.string());
    }

    if (plan.mode == "dev") {
        if (!plan.repo_root.has_value() || !fs::exists(*plan.repo_root)) {
            result.errors.push_back("dev mode repository root is missing");
        }
        if (!plan.pythonpath.has_value() || !fs::exists(*plan.pythonpath)) {
            result.errors.push_back("dev mode PYTHONPATH root is missing");
        }
    }

    if (plan.mode == "prod") {
        if (!plan.manifest_path.has_value() || !fs::exists(*plan.manifest_path)) {
            result.errors.push_back("prod mode runtime manifest is missing");
        }
        if (plan.pythonpath.has_value() && !fs::exists(*plan.pythonpath)) {
            result.errors.push_back(
                "configured AIRUNNER_PYTHONPATH does not exist: "
                + plan.pythonpath->string());
        }
    }

    if (plan.llama_server_bin.has_value() && !fs::exists(*plan.llama_server_bin)) {
        result.warnings.push_back(
            "configured AIRUNNER_LLAMA_SERVER_BIN does not exist: "
            + plan.llama_server_bin->string());
    }

    if (plan.whisper_server_bin.has_value()
        && !fs::exists(*plan.whisper_server_bin)) {
        result.warnings.push_back(
            "configured AIRUNNER_WHISPER_SERVER_BIN does not exist: "
            + plan.whisper_server_bin->string());
    }

    return result;
}

void print_validation(const ValidationResult &validation)
{
    for (const auto &warning : validation.warnings) {
        std::cerr << "warning: " << warning << '\n';
    }
    for (const auto &error : validation.errors) {
        std::cerr << "error: " << error << '\n';
    }
}

std::map<std::string, std::string> build_environment(const LaunchPlan &plan)
{
    std::map<std::string, std::string> env;
    env["AIRUNNER_LAUNCH_MODE"] = plan.mode;
    env["AIRUNNER_BUNDLE_ROOT"] = plan.bundle_root.string();
    env["AIRUNNER_PYTHON"] = plan.python_executable.string();
    env["AIRUNNER_NATIVE_LAUNCHER"] = current_executable_path().string();
    env["DEV_ENV"] = plan.mode == "dev" ? "1" : "0";

    if (plan.manifest_path.has_value()) {
        env["AIRUNNER_RUNTIME_MANIFEST"] = plan.manifest_path->string();
    }

    const auto pythonpath = merge_pythonpath(plan.pythonpath);
    if (!pythonpath.empty()) {
        env["PYTHONPATH"] = pythonpath;
    }

    if (plan.llama_server_bin.has_value()) {
        env["AIRUNNER_LLAMA_SERVER_BIN"] = plan.llama_server_bin->string();
    }
    if (plan.whisper_server_bin.has_value()) {
        env["AIRUNNER_WHISPER_SERVER_BIN"] =
            plan.whisper_server_bin->string();
    }

    return env;
}

#ifdef _WIN32
int run_process(
    const fs::path &python_executable,
    const std::string &entrypoint,
    const std::vector<std::string> &app_args,
    const std::map<std::string, std::string> &environment,
    bool no_fork)
{
    for (const auto &[key, value] : environment) {
        _putenv_s(key.c_str(), value.c_str());
    }

    std::vector<std::string> args = {
        python_executable.string(), "-m", entrypoint,
    };
    args.insert(args.end(), app_args.begin(), app_args.end());

    std::vector<char *> argv;
    argv.reserve(args.size() + 1);
    for (auto &arg : args) {
        argv.push_back(arg.data());
    }
    argv.push_back(nullptr);

    const int exit_code = _spawnv(
        _P_WAIT,
        python_executable.string().c_str(),
        argv.data());
    if (exit_code == -1) {
        throw std::runtime_error("Failed to spawn Python process");
    }
    return exit_code;
}
#else
int run_process(
    const fs::path &python_executable,
    const std::string &entrypoint,
    const std::vector<std::string> &app_args,
    const std::map<std::string, std::string> &environment,
    bool no_fork)
{
    std::vector<std::string> args = {
        python_executable.string(), "-m", entrypoint,
    };
    args.insert(args.end(), app_args.begin(), app_args.end());

    std::vector<char *> argv;
    argv.reserve(args.size() + 1);
    for (auto &arg : args) {
        argv.push_back(arg.data());
    }
    argv.push_back(nullptr);

    if (no_fork) {
        for (const auto &[key, value] : environment) {
            setenv(key.c_str(), value.c_str(), 1);
        }

        execv(python_executable.c_str(), argv.data());
        throw std::runtime_error(
            "execv() failed for --no-fork mode: " + std::string(strerror(errno)));
    }

    SignalForwardingGuard signal_forwarding_guard;
    const pid_t pid = fork();
    if (pid < 0) {
        throw std::runtime_error("fork() failed");
    }

    if (pid == 0) {
        setpgid(0, 0);

        for (const auto &[key, value] : environment) {
            setenv(key.c_str(), value.c_str(), 1);
        }

        execv(python_executable.c_str(), argv.data());
        std::perror("execv");
        _exit(127);
    }

    g_child_process_group = static_cast<sig_atomic_t>(pid);
    if (setpgid(pid, pid) < 0 && errno != EACCES && errno != ESRCH) {
        throw std::runtime_error("setpgid() failed");
    }

    int status = 0;
    while (true) {
        const pid_t waited_pid = waitpid(pid, &status, 0);
        if (waited_pid == pid) {
            break;
        }
        if (waited_pid < 0 && errno == EINTR) {
            continue;
        }
        if (waited_pid < 0) {
            throw std::runtime_error("waitpid() failed");
        }
    }

    g_child_process_group = 0;

    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    return 1;
}
#endif

} // namespace

int main(int argc, char **argv)
{
    try {
        const auto options = parse_args(argc, argv);
        const auto plan = resolve_plan(options);
        const auto validation = validate_plan(plan);
        if (options.print_plan) {
            print_plan(plan);
        }
        print_validation(validation);

        if (options.diagnose) {
            return validation.ok() ? 0 : 2;
        }
        if (!validation.ok()) {
            return 2;
        }
        if (options.dry_run) {
            return 0;
        }
        const auto environment = build_environment(plan);
        return run_process(
            plan.python_executable,
            plan.entrypoint,
            plan.app_args,
            environment,
            options.no_fork);
    } catch (const std::exception &error) {
        std::cerr << "airunner launcher error: " << error.what() << '\n';
        return 1;
    }
}