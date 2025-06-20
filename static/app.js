const Vue = window.Vue
const axios = window.axios

new Vue({
  el: "#app",
  data: {
    isLoggedIn: false,
    username: "",
    password: "",
    newNote: "",
    notes: [],
    message: "",
    messageType: "",
    visitUrl: "",
    instanceId: "",
    showToast: false,
    toastType: "success",
    toastIcon: "fas fa-check-circle",
    toastProgress: 100,
    toastTimer: null,
    toastDuration: 5000,
  },
  created() {
    this.instanceId = this.getCookie("INSTANCE") || "unknown"
    this.checkLoginStatus()
  },
  methods: {
    showNotification(message, type = "success") {
      if (this.toastTimer) {
        clearInterval(this.toastTimer)
        clearTimeout(this.hideTimer)
      }

      this.message = message
      this.messageType = type
      this.toastType = type

      const iconMap = {
        success: "fas fa-check-circle",
        error: "fas fa-exclamation-circle",
        warning: "fas fa-exclamation-triangle",
      }
      this.toastIcon = iconMap[type] || iconMap.success

      this.showToast = true
      this.toastProgress = 100

      const intervalTime = 50
      const steps = this.toastDuration / intervalTime
      const decrementPerStep = 100 / steps

      this.toastTimer = setInterval(() => {
        this.toastProgress -= decrementPerStep
        if (this.toastProgress <= 0) {
          this.hideToast()
        }
      }, intervalTime)

      this.hideTimer = setTimeout(() => {
        this.hideToast()
      }, this.toastDuration)
    },

    hideToast() {
      if (this.toastTimer) {
        clearInterval(this.toastTimer)
        this.toastTimer = null
      }

      const toast = document.querySelector(".toast-notification")
      if (toast) {
        toast.style.animation = "slideOutRight 0.3s forwards"

        setTimeout(() => {
          this.showToast = false
        }, 300)
      } else {
        this.showToast = false
      }
    },

    getCookie(name) {
      const value = `; ${document.cookie}`
      const parts = value.split(`; ${name}=`)
      if (parts.length === 2) return parts.pop().split(";").shift()
      return ""
    },

    checkLoginStatus() {
      const currentPage = window.location.pathname
      if (currentPage === "/index" || currentPage === "/") {
        axios
          .get("/api/status")
          .then((response) => {
            if (response.data.loggedIn) {
              this.isLoggedIn = true
              this.username = response.data.username
              this.instanceId = response.data.instance
              this.fetchNotes()
            }
          })
          .catch((error) => {
            console.error("Error checking login status:", error)
          })
      }
    },

    register() {
      axios
        .post("/api/register", { username: this.username, password: this.password })
        .then((response) => {
          this.showNotification(response.data.message, "success")
        })
        .catch((error) => {
          this.showNotification(error.response.data.message, "error")
        })
    },

    login() {
      axios
        .post("/api/login", { username: this.username, password: this.password })
        .then((response) => {
          this.isLoggedIn = true
          this.showNotification(response.data.message, "success")
          this.fetchNotes()
        })
        .catch((error) => {
          this.showNotification(error.response.data.message, "error")
        })
    },

    logout() {
      axios.post("/api/logout").then((response) => {
        this.isLoggedIn = false
        this.username = ""
        this.password = ""
        this.notes = []
        this.showNotification(response.data.message, "success")
      })
    },

    fetchNotes() {
      axios.get("/api/notes").then((response) => {
        this.notes = response.data.notes.map((note) => {
          if (note.download_link) {
            return {
              ...note,
              content: `${note.content} <a href="${note.download_link}" class="download-button" target="_blank" title="Download ${note.filename}"><i class="fas fa-download"></i></a>`,
            }
          }
          return note
        })
      })
    },

    addNote() {
      axios
        .post("/api/notes", { content: this.newNote })
        .then((response) => {
          this.showNotification(response.data.message, "success")
          this.newNote = ""
          this.fetchNotes()
        })
        .catch((error) => {
          this.showNotification(error.response.data.message, "error")
        })
    },

    deleteNote(noteId) {
      axios
        .delete("/api/notes/" + noteId)
        .then((response) => {
          this.showNotification(response.data.message, "success")
          this.fetchNotes()
        })
        .catch((error) => {
          this.showNotification(error.response.data.message, "error")
        })
    },

    uploadFile(event) {
      const file = event.target.files[0]
      if (!file) return

      const formData = new FormData()
      formData.append("file", file)

      axios
        .post("/api/notes/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        .then((response) => {
          this.showNotification(response.data.message, "success")
          this.fetchNotes()
        })
        .catch((error) => {
          this.showNotification(error.response.data.message, "error")
        })
    },

    startBot() {
      if (!this.visitUrl) {
        this.showNotification("Please enter a valid URL.", "error")
        return
      }

      axios
        .post("/api/visit", { url: this.visitUrl })
        .then((response) => {
          if (response.data.status === "url_valid") {
            this.showNotification(response.data.message, "warning")

            setTimeout(() => {
              this.showNotification("Page visited successfully!", "success")
            }, 2000)
          } else {
            this.showNotification(response.data.message || "Report sent successfully!", "success")
          }
        })
        .catch((error) => {
          this.showNotification(error.response?.data?.message || "An error occurred.", "error")
        })
    },
  },
})

