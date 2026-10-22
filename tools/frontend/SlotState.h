// Independent physical-media state; no UI, filesystem or launcher side effects.
// Copyright 2026, MIT. Shared by the frontend extension and native state tests.
#pragma once
#include <algorithm>
#include <string>

namespace slot {
enum class Phase { Empty, Inserting, Inserted, Ejecting, Closing, Powering, Zooming, Launching, Running };

class State {
public:
    Phase phase() const { return mPhase; }
    const std::string& inserted() const { return mInserted; }
    const std::string& target() const { return mTarget; }
    const std::string& desired() const { return mDesired; }
    float progress() const { return mProgress; }
    float duration() const { return mDuration; }
    bool busy() const { return mPhase == Phase::Inserting || mPhase == Phase::Ejecting; }
    bool closing() const { return mPhase == Phase::Closing; }
    bool preparing() const { return mPhase==Phase::Powering || mPhase==Phase::Zooming; }
    bool launching() const { return closing() || preparing() || mPhase == Phase::Launching || mPhase == Phase::Running; }

    void insert(const std::string& game) {
        if (launching() || game.empty()) return;
        mLaunch.clear();
        mCloseReady=false;
        mPresentationReady=false;
        mDesired = game;
        reconcile();
    }
    void eject() {
        if (launching()) return;
        mLaunch.clear();
        mDesired.clear();
        reconcile();
    }
    void play(const std::string& game) {
        if (launching() || game.empty()) return;
        mLaunch = mDesired = game;
        mCloseReady=false;
        mPresentationReady=false;
        reconcile();
    }
    void update(float seconds) {
        if(preparing()) {
            mProgress=std::min(1.f,mProgress+std::max(0.f,std::min(seconds,.1f))/mDuration);
            if(mProgress>=1){if(mPhase==Phase::Powering&&mZoomDuration>0){mPhase=Phase::Zooming;mProgress=0;mDuration=mZoomDuration;}else{mPresentationReady=true;mPhase=Phase::Inserted;}}
            return;
        }
        if(closing()) {
            mProgress=std::min(1.f,mProgress+std::max(0.f,std::min(seconds,.1f))/mDuration);
            if(mProgress>=1){mCloseReady=true;mPhase=Phase::Inserted;}
            return;
        }
        if (!busy()) return;
        // A suspended window must not finish an entire swap in one giant tick.
        mProgress = std::min(1.f, mProgress + std::max(0.f, std::min(seconds, .1f)) / mDuration);
        if (mProgress < 1.f) return;
        if (mPhase == Phase::Inserting) {
            mInserted = mTarget;
            mPhase = Phase::Inserted;
        } else {
            mInserted.clear();
            mPhase = Phase::Empty;
        }
        mTarget.clear();
        reconcile();
    }
    // Called by the view only after the ordinary launch checks have succeeded.
    // A launch is handed out once, regardless of additional update/confirm calls.
    std::string takeLaunch() {
        if (mPhase != Phase::Inserted || mLaunch.empty() || mLaunch != mInserted) return {};
        if(mCloseDuration>0&&!mCloseReady) {
            mPhase=Phase::Closing;mProgress=0;mDuration=mCloseDuration;return {};
        }
        if(!mPresentationReady&&(mPowerDuration>0||mZoomDuration>0)) {
            mPhase=mPowerDuration>0?Phase::Powering:Phase::Zooming;mProgress=0;mDuration=mPowerDuration>0?mPowerDuration:mZoomDuration;return {};
        }
        std::string game = mLaunch;
        mLaunch.clear();
        mPhase = Phase::Launching;
        return game;
    }
    void running() { if (mPhase == Phase::Launching) mPhase = Phase::Running; }
    void cancelLaunch(){if(preparing()){mPhase=Phase::Inserted;mDesired=mInserted;mLaunch.clear();mProgress=0;mPresentationReady=false;}}
    void presentationDurations(float power,float zoom){mPowerDuration=std::max(0.f,power);mZoomDuration=std::max(0.f,zoom);}
    void returned() {
        if (launching()) {
            mPhase = mInserted.empty() ? Phase::Empty : Phase::Inserted;
            mDesired = mInserted;
            mLaunch.clear();
            mPresentationReady=false;
        }
    }
    void invalidate(const std::string& game) {
        if (mInserted == game || mTarget == game || mLaunch == game) reset();
        else if (mDesired == game) mDesired = mInserted;
    }
    void reset() { *this = State(); }
    // Leaving a room is not an eject. Finish the latest media command without
    // carrying a queued launch into another view. Actual emulator handoff keeps
    // its Launching/Running marker until returned() releases launch ownership.
    void park() {
        if(mPhase==Phase::Launching||mPhase==Phase::Running)return;
        mInserted=mDesired;mTarget.clear();mLaunch.clear();mProgress=0;
        mCloseReady=mPresentationReady=false;
        mPhase=mInserted.empty()?Phase::Empty:Phase::Inserted;
    }
    void durations(float insertSeconds, float ejectSeconds,float closeSeconds=0) {
        mInsertDuration = std::max(.05f, insertSeconds);
        mEjectDuration = std::max(.05f, ejectSeconds);
        mCloseDuration=std::max(0.f,closeSeconds);
    }

private:
    void reconcile() {
        if (busy() || launching()) return;
        if (!mInserted.empty() && mInserted != mDesired) {
            mPhase = Phase::Ejecting;
            mTarget = mInserted;
            mDuration = mEjectDuration;
        } else if (mInserted.empty() && !mDesired.empty()) {
            mPhase = Phase::Inserting;
            mTarget = mDesired;
            mDuration = mInsertDuration;
        } else return;
        mProgress = 0;
    }
    Phase mPhase = Phase::Empty;
    std::string mInserted, mTarget, mDesired, mLaunch;
    float mProgress = 0, mDuration = 1, mInsertDuration = .9f, mEjectDuration = .7f;
    float mCloseDuration=0;
    float mPowerDuration=0,mZoomDuration=0;bool mPresentationReady=false;
    bool mCloseReady=false;
};
}
