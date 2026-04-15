import { useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  HeartPulse,
  MessageCircleHeart,
  Microscope,
  Play,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import medicalHeroPortrait from "../assets/medical-hero-portrait.svg";
import medicalReviewPortrait from "../assets/medical-review-portrait.svg";
import reportIllustration from "../assets/report-illustration.svg";

const services = [
  {
    icon: ScanSearch,
    title: "Medical Report Analysis",
    body: "Upload blood work, discharge summaries, or scans and get structured findings with patient-friendly wording.",
    tag: "Most used",
    actionLabel: "Analyze now",
    action: "analysis",
    featured: true,
  },
  {
    icon: ClipboardList,
    title: "Lab Value Interpretation",
    body: "Turn scattered values into trends, flagged concerns, suggested tests, and doctor-ready notes.",
    tag: "Guided review",
    actionLabel: "Open workspace",
    action: "analysis",
  },
  {
    icon: Bot,
    title: "Friendly Medical RAG Chat",
    body: "Ask grounded follow-up questions and keep the conversation anchored to your uploaded reports and trusted context.",
    tag: "Customer friendly",
    actionLabel: "Open chat",
    action: "chat",
  },
  {
    icon: Stethoscope,
    title: "Next-Step Care Support",
    body: "Get suggestions for precautions, likely specialists, diet notes, and preparation before speaking with a clinician.",
    tag: "Practical steps",
    actionLabel: "See flow",
    action: "analysis",
  },
];

const reasons = [
  {
    icon: ShieldCheck,
    title: "Simple and reassuring",
    body: "We translate medical wording into calm, understandable summaries without losing the details that matter.",
  },
  {
    icon: BrainCircuit,
    title: "Grounded by your reports",
    body: "The chatbot uses report summaries and ingested medical documents so answers stay closer to the actual case.",
  },
  {
    icon: Microscope,
    title: "Built for real medical flows",
    body: "Upload, interpret, chart, and ask follow-up questions in one workspace instead of juggling separate tools.",
  },
];

const programs = [
  {
    title: "Patient Workspace",
    body: "Keep uploaded reports, extracted values, and suggested next questions in one place for easier follow-up visits.",
    highlights: ["Upload PDFs and report images", "See structured findings fast", "Return later with synced history"],
    actionLabel: "Open workspace",
    action: "analysis",
    featured: true,
  },
  {
    title: "RAG Care Chat",
    body: "Use the assistant after analysis to ask what results mean, what to monitor next, and how to prepare for a doctor visit.",
    highlights: ["Friendly tone for non-clinical users", "Uses recent report context", "Great for next-step questions"],
    actionLabel: "Start chatting",
    action: "chat",
  },
];

const experts = [
  { name: "Dr. Iyer", role: "Lab review", className: "hero-avatar--one" },
  { name: "Dr. Shah", role: "Care chat", className: "hero-avatar--two" },
  { name: "Dr. Ali", role: "Reports", className: "hero-avatar--three" },
];

function LandingPage({ user, testimonials = [], onExploreWorkspace, onOpenAuth, onOpenChat }) {
  const [testimonialIndex, setTestimonialIndex] = useState(0);
  const testimonialItems = testimonials;

  useEffect(() => {
    const elements = Array.from(document.querySelectorAll("[data-reveal]"));

    if (!elements.length) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      elements.forEach((element) => element.classList.add("is-visible"));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -8% 0px" }
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!testimonialItems.length) return undefined;
    const timer = window.setInterval(() => {
      setTestimonialIndex((current) => (current + 1) % testimonialItems.length);
    }, 6500);

    return () => window.clearInterval(timer);
  }, [testimonialItems]);

  useEffect(() => {
    if (testimonialIndex >= testimonialItems.length) {
      setTestimonialIndex(0);
    }
  }, [testimonialIndex, testimonialItems.length]);

  function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    section?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleAction(action) {
    if (action === "chat") {
      onOpenChat();
      return;
    }
    onExploreWorkspace();
  }

  function renderHeroActions(extraClassName = "") {
    return (
      <div className={`hero-actions ${extraClassName}`.trim()}>
        <button className="primary-btn" onClick={onExploreWorkspace} type="button">
          <span>Open Workspace</span>
          <ArrowRight size={16} />
        </button>
        <button
          className="ghost-btn"
          onClick={user ? onOpenChat : () => onOpenAuth("login")}
          type="button"
        >
          <span>{user ? "Open Chat" : "Login"}</span>
        </button>
      </div>
    );
  }

  function renderHeroLink(extraClassName = "") {
    return (
      <button className={`hero-link ${extraClassName}`.trim()} onClick={() => scrollToSection("services")} type="button">
        <span>See services</span>
        <ArrowUpRight size={16} />
      </button>
    );
  }

  const activeTestimonial = testimonialItems[testimonialIndex] || testimonialItems[0] || null;

  return (
    <div className="landing-page">
      <section className="landing-hero" id="home">
        <div className="landing-hero__content">
          <div className="landing-hero__copy" data-reveal style={{ "--reveal-delay": "40ms" }}>
            <span className="eyebrow">Trusted support for medical report understanding</span>
            <h1>
              The best partner
              <br />
              for clearer reports
            </h1>
            <p>
              HealthNova combines medical report analysis with a customer-friendly RAG chatbot so
              patients and families can understand findings, ask follow-up questions, and prepare for care conversations.
            </p>

            <div className="hero-statline">
              <span className="hero-pill hero-pill--soft">
                <Sparkles size={15} />
                OCR + structured extraction
              </span>
              <span className="hero-pill hero-pill--soft">
                <HeartPulse size={15} />
                Grounded medical follow-up
              </span>
            </div>

            {renderHeroActions("hero-actions--desktop")}

            {renderHeroLink("hero-link--desktop")}
          </div>

          <div className="landing-hero__visual" data-reveal style={{ "--reveal-delay": "150ms" }}>
            <div className="hero-scene">
              <div className="hero-scene__wave" />
              <div className="hero-scene__ring hero-scene__ring--outer" />
              <div className="hero-scene__ring hero-scene__ring--inner" />

              <div className="hero-card hero-card--top">
                <span className="hero-card__kicker">32 values extracted</span>
                <strong>RBC, HbA1c, glucose, thyroid, kidney and more</strong>
              </div>

              <div className="hero-card hero-card--right">
                <span className="hero-card__kicker">Friendly medical chat</span>
                <strong>Grounded answers for patients and caregivers</strong>
              </div>

              <div className="hero-scene__photo">
                <img src={medicalHeroPortrait} alt="Illustration of a patient holding a medical report" />
              </div>

              <button className="hero-play" onClick={() => scrollToSection("testimonials")} type="button">
                <Play size={16} />
              </button>

              {experts.map((expert) => (
                <div className={`hero-avatar ${expert.className}`} key={expert.name}>
                  <span>{expert.name.slice(0, 2).toUpperCase()}</span>
                  <small>{expert.role}</small>
                </div>
              ))}
            </div>
          </div>

          {renderHeroActions("hero-actions--mobile")}
          {renderHeroLink("hero-link--mobile")}
        </div>
      </section>

      <section className="marketing-section services-section" id="services">
        <div className="section-heading section-heading--center" data-reveal>
          <h2>Our Services</h2>
          <p>
            A medical analysis experience designed to feel as approachable as a consumer app,
            while still keeping the report details structured and useful.
          </p>
        </div>

        <div className="services-grid">
          {services.map((service, index) => {
            const Icon = service.icon;
            return (
              <article
                className={`service-card ${service.featured ? "service-card--featured" : ""}`}
                key={service.title}
                data-reveal
                style={{ "--reveal-delay": `${index * 70 + 40}ms` }}
              >
                <div className="service-card__icon">
                  <Icon size={22} />
                </div>
                <div className="service-card__copy">
                  <strong>{service.title}</strong>
                  <p>{service.body}</p>
                </div>
                <div className="service-card__footer">
                  <span className="service-card__tag">{service.tag}</span>
                  <button className="text-link" onClick={() => handleAction(service.action)} type="button">
                    {service.actionLabel} <ArrowUpRight size={15} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="marketing-section why-section" id="advantages">
        <div className="why-layout">
          <div className="why-layout__visual" data-reveal>
            <div className="why-collage">
              <div className="why-collage__bubble why-collage__bubble--main">
                <img src={reportIllustration} alt="Illustration of a medical report summary card" />
              </div>
              <div className="why-collage__bubble why-collage__bubble--side">
                <span>AI</span>
                <small>Report parsing</small>
              </div>
              <div className="why-collage__bubble why-collage__bubble--bottom">
                <span>MD</span>
                <small>Care prep</small>
              </div>
              <div className="why-collage__bubble why-collage__bubble--mini">
                <Sparkles size={16} />
              </div>
            </div>
          </div>

          <div className="why-layout__copy" data-reveal style={{ "--reveal-delay": "120ms" }}>
            <div className="section-heading">
              <h2>Why should you choose HealthNova?</h2>
            </div>

            <div className="reason-list">
              {reasons.map((reason) => {
                const Icon = reason.icon;
                return (
                  <article className="reason-item" key={reason.title}>
                    <div className="reason-item__icon">
                      <Icon size={18} />
                    </div>
                    <div>
                      <strong>{reason.title}</strong>
                      <p>{reason.body}</p>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="marketing-section programs-section" id="programs">
        <div className="programs-layout">
          <div className="programs-copy" data-reveal>
            <span className="eyebrow">Other programs</span>
            <h2>Support beyond one report</h2>
            <p>
              HealthNova is more than a single upload screen. It gives patients a repeatable flow
              for review, follow-up chat, and better preparation for doctor conversations.
            </p>
          </div>

          <div className="programs-showcase" data-reveal style={{ "--reveal-delay": "120ms" }}>
            {programs.map((program) => (
              <article
                className={`program-card ${program.featured ? "program-card--featured" : "program-card--secondary"}`}
                key={program.title}
              >
                <div className="program-card__icon">
                  {program.featured ? <ShieldCheck size={22} /> : <MessageCircleHeart size={22} />}
                </div>
                <strong>{program.title}</strong>
                <p>{program.body}</p>
                <div className="program-list">
                  {program.highlights.map((highlight) => (
                    <div className="program-list__item" key={highlight}>
                      <CheckCircle2 size={14} />
                      <span>{highlight}</span>
                    </div>
                  ))}
                </div>
                <button className={program.featured ? "primary-btn" : "ghost-btn"} onClick={() => handleAction(program.action)} type="button">
                  {program.actionLabel}
                </button>
              </article>
            ))}
            <div className="programs-showcase__dots">
              <span />
              <span />
            </div>
          </div>
        </div>
      </section>

      <section className="marketing-section testimonial-section" id="testimonials">
        <div className="section-heading section-heading--center" data-reveal>
          <h2>What our customers are saying</h2>
          <p>
            HealthNova is designed to reduce confusion around medical reports and make
            follow-up questions feel approachable.
          </p>
        </div>

        <div className="testimonial-shell" data-reveal style={{ "--reveal-delay": "120ms" }}>
          {activeTestimonial ? (
            <>
              <button
                className="testimonial-nav"
                onClick={() => setTestimonialIndex((current) => (current - 1 + testimonialItems.length) % testimonialItems.length)}
                type="button"
                aria-label="Previous testimonial"
                disabled={testimonialItems.length <= 1}
              >
                <ChevronLeft size={18} />
              </button>

              <article className="testimonial-card">
                <div className="testimonial-card__media">
                  <div className="testimonial-card__portrait">
                    <img src={medicalReviewPortrait} alt="Illustration of a customer sharing their experience" />
                  </div>
                  <div className="testimonial-card__badge">
                    <span>{activeTestimonial.badge}</span>
                  </div>
                </div>

                <div className="testimonial-card__copy">
                  <span className="testimonial-mark">"</span>
                  <p>{activeTestimonial.quote}</p>
                  <strong>{activeTestimonial.name}</strong>
                  <span>{activeTestimonial.role}</span>
                </div>
              </article>

              <button
                className="testimonial-nav testimonial-nav--next"
                onClick={() => setTestimonialIndex((current) => (current + 1) % testimonialItems.length)}
                type="button"
                aria-label="Next testimonial"
                disabled={testimonialItems.length <= 1}
              >
                <ChevronRight size={18} />
              </button>
            </>
          ) : (
            <article className="testimonial-card testimonial-card--empty">
              <div className="testimonial-card__media testimonial-card__media--empty">
                <div className="testimonial-card__portrait">
                  <img src={medicalReviewPortrait} alt="Illustration of a customer sharing their experience" />
                </div>
                <div className="testimonial-card__badge">
                  <span>Real reviews appear here</span>
                </div>
              </div>

              <div className="testimonial-card__copy testimonial-card__copy--empty">
                <span className="testimonial-mark">"</span>
                <p>No public feedback yet. The first real user review will appear here.</p>
                <strong>HealthNova</strong>
                <span>Waiting for the first submitted feedback</span>
              </div>
            </article>
          )}
        </div>
      </section>

      <footer className="site-footer" id="contact">
        <div className="site-footer__grid">
          <div className="site-footer__brand">
            <div className="site-footer__logo">
              <span className="brand__pulse" />
              <strong>HealthNova</strong>
            </div>
            <p>
              Customer-friendly medical report analysis and grounded RAG chat for patients,
              caregivers, and follow-up care preparation.
            </p>
            <div className="site-footer__actions">
              <button className="ghost-btn ghost-btn--footer" onClick={onExploreWorkspace} type="button">
                Open workspace
              </button>
              {!user ? (
                <button className="ghost-btn ghost-btn--footer" onClick={() => onOpenAuth("login")} type="button">
                  Login
                </button>
              ) : null}
            </div>
          </div>

          <div>
            <h3>Platform</h3>
            <a href="#services">Report analysis</a>
            <a href="#advantages">Why choose us</a>
            <a href="#programs">Care paths</a>
            <a href="#testimonials">Testimonials</a>
          </div>

          <div>
            <h3>Use Cases</h3>
            <a href="#services">Blood report review</a>
            <a href="#services">Imaging summary support</a>
            <a href="#programs">Doctor visit prep</a>
            <a href="#programs">Family caregiver support</a>
          </div>

          <div>
            <h3>Contact</h3>
            <a href="mailto:ojaswimakode7@gmail.com">ojaswimakode7@gmail.com</a>
            <a href="https://www.linkedin.com/in/ojawsi-makode-517055291/" target="_blank" rel="noreferrer">
              LinkedIn profile
            </a>
            <span className="site-footer__note">
              This product supports understanding and preparation, not diagnosis or emergency care.
            </span>
          </div>
        </div>

        <div className="site-footer__bottom">
          <span>All rights reserved.</span>
          <span>Developed and managed by Ojaswi Makode.</span>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;

