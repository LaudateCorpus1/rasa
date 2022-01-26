from typing import Text, Dict, List, Optional

import numpy as np
import pytest

from rasa.core.featurizers.single_state_featurizer import SingleStateFeaturizer
from rasa.core.featurizers.max_history_tracker_featurizer import (
    MaxHistoryTrackerFeaturizer,
)
from rasa.shared.core.domain import Domain
from rasa.shared.nlu.interpreter import RegexInterpreter
from tests.core.utilities import user_uttered
from rasa.shared.nlu.training_data.features import Features
from rasa.shared.nlu.constants import INTENT, ACTION_NAME
from rasa.shared.core.constants import (
    ACTION_LISTEN_NAME,
    ACTION_UNLIKELY_INTENT_NAME,
    USER,
    PREVIOUS_ACTION,
)
from rasa.shared.core.events import ActionExecuted
from rasa.shared.core.trackers import DialogueStateTracker


def compare_featurized_states(
    states1: List[Dict[Text, List[Features]]], states2: List[Dict[Text, List[Features]]]
) -> bool:
    """Compares two lists of featurized states and returns True if they
    are identical and False otherwise.
    """

    if len(states1) != len(states2):
        return False

    for state1, state2 in zip(states1, states2):
        if state1.keys() != state2.keys():
            return False
        for key in state1.keys():
            for feature1, feature2 in zip(state1[key], state2[key]):
                if np.any((feature1.features != feature2.features).toarray()):
                    return False

                # NOTE: we change the origin information in the rework
                # if feature1.origin != feature2.origin:
                #    return False

                if feature1.attribute != feature2.attribute:
                    return False
                if feature1.type != feature2.type:
                    return False
    return True


### FEATURIZE TRACKERS:  featurization during training


@pytest.mark.parametrize("max_history", [None, 2])
def test_featurize_trackers_for_states_with_action_and_intent_only(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    max_history: Optional[int],
):
    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )

    actual_features, actual_labels, entity_tags = tracker_featurizer.featurize_trackers(
        [moodbot_tracker], moodbot_domain, RegexInterpreter()
    )

    expected_features = [
        [{},],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_did_that_help"]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_did_that_help"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["deny"]],
            },
        ],
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]

    assert actual_features is not None
    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)

    expected_labels = np.array([[0, 15, 0, 12, 13, 0, 14]]).T

    assert actual_labels is not None
    assert actual_labels.shape == expected_labels.shape
    assert np.all(actual_labels == expected_labels)

    # moodbot doesn't contain e2e entities
    assert not any([any(turn_tags) for turn_tags in entity_tags])


@pytest.mark.parametrize("max_history", [None, 2])
def test_featurize_trackers_ignore_action_unlikely_intent(
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    max_history: Optional[int],
):
    tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_greet"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("mood_unhappy"),
        ],
        domain=moodbot_domain,
    )
    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history,
    )

    actual_features, actual_labels, entity_tags = tracker_featurizer.featurize_trackers(
        [tracker],
        moodbot_domain,
        RegexInterpreter(),
        ignore_action_unlikely_intent=True,
    )

    expected_features = [
        [{},],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
        ],
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]

    assert actual_features is not None

    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)

    expected_labels = np.array([[0, 15, 0]]).T
    assert actual_labels.shape == expected_labels.shape
    for actual, expected in zip(actual_labels, expected_labels):
        assert np.all(actual == expected)

    # moodbot doesn't contain e2e entities
    assert not any([any(turn_tags) for turn_tags in entity_tags])


@pytest.mark.parametrize("max_history", [None, 2])
def test_featurize_trackers_keep_action_unlikely_intent(
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    max_history: Optional[int],
):
    tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_greet"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("mood_unhappy"),
        ],
        domain=moodbot_domain,
    )
    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history,
    )

    actual_features, actual_labels, entity_tags = tracker_featurizer.featurize_trackers(
        [tracker], moodbot_domain, RegexInterpreter(),
    )

    expected_features = [
        [{},],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"][ACTION_UNLIKELY_INTENT_NAME]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"][ACTION_UNLIKELY_INTENT_NAME]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
        ],
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]

    assert actual_features is not None
    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)

    expected_labels = np.array([[0, 9, 15, 0]]).T
    assert actual_labels is not None
    assert actual_labels.shape == expected_labels.shape
    for actual, expected in zip(actual_labels, expected_labels):
        assert np.all(actual == expected)

    # moodbot doesn't contain e2e entities
    assert not any([any(turn_tags) for turn_tags in entity_tags])


@pytest.mark.parametrize(
    "remove_duplicates,max_history",
    [[True, None], [True, 2], [False, None], [False, 2],],
)
def test_deduplicate_and_featurize_trackers(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    remove_duplicates: bool,
    max_history: Optional[int],
):
    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history, remove_duplicates=remove_duplicates
    )

    # Add Duplicate moodbot_tracker states should get removed.
    actual_features, actual_labels, entity_tags = tracker_featurizer.featurize_trackers(
        [moodbot_tracker, moodbot_tracker], moodbot_domain, RegexInterpreter()
    )

    # FIXME : deduplicate this

    expected_features = [
        [{},],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_did_that_help"]]},
        ],
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_did_that_help"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["deny"]],
            },
        ],
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]
    if not remove_duplicates:
        expected_features = expected_features * 2

    assert actual_features is not None
    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)

    expected_labels = np.array([[0, 15, 0, 12, 13, 0, 14]]).T
    if not remove_duplicates:
        expected_labels = np.vstack([expected_labels] * 2)

    assert actual_labels is not None
    assert actual_labels.shape == expected_labels.shape
    assert np.all(actual_labels == expected_labels)

    # moodbot doesn't contain e2e entities
    assert not any([any(turn_tags) for turn_tags in entity_tags])


###  CREATE STATE FEATURES: featurization during inference

"""

@pytest.mark.parametrize("max_history", [None, 2])
def test_create_state_features(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    max_history: Optional[int],
):
    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )
    interpreter = RegexInterpreter()
    state_featurizer.prepare_for_training(moodbot_domain, interpreter)
    actual_features = tracker_featurizer.create_state_features(
        [moodbot_tracker], moodbot_domain, interpreter
    )

    expected_features = [
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_unhappy"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_cheer_up"]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_did_that_help"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["deny"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_goodbye"]]},
        ]
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]

    assert actual_features is not None
    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)


@pytest.mark.parametrize("max_history", [None, 2])
def test_create_state_features_ignore_action_unlikely_intent(
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    max_history: Optional[int],
):
    tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_greet"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("mood_great"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_happy"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("goodbye"),
        ],
        domain=moodbot_domain,
    )

    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )
    interpreter = RegexInterpreter()
    state_featurizer.prepare_for_training(moodbot_domain, interpreter)
    actual_features = tracker_featurizer.create_state_features(
        [tracker], moodbot_domain, interpreter, ignore_action_unlikely_intent=True
    )

    expected_features = [
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_great"]],
            },
            {ACTION_NAME: [moodbot_features["actions"]["utter_happy"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["goodbye"]],
            },
        ]
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]

    assert actual_features is not None
    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)


@pytest.mark.parametrize("max_history", [None, 2])
def test_create_state_features_keep_action_unlikely_intent(
    moodbot_domain: Domain,
    moodbot_features: Dict[Text, Dict[Text, Features]],
    max_history: Optional[int],
):
    tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_greet"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("mood_great"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_happy"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("goodbye"),
        ],
        domain=moodbot_domain,
    )

    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )
    interpreter = RegexInterpreter()
    state_featurizer.prepare_for_training(moodbot_domain, interpreter)
    actual_features = tracker_featurizer.create_state_features(
        [tracker], moodbot_domain, interpreter,
    )

    expected_features = [
        [
            {},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["greet"]],
            },
            {ACTION_NAME: [moodbot_features["actions"][ACTION_UNLIKELY_INTENT_NAME]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_greet"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["mood_great"]],
            },
            {ACTION_NAME: [moodbot_features["actions"][ACTION_UNLIKELY_INTENT_NAME]]},
            {ACTION_NAME: [moodbot_features["actions"]["utter_happy"]]},
            {
                ACTION_NAME: [moodbot_features["actions"][ACTION_LISTEN_NAME]],
                INTENT: [moodbot_features["intents"]["goodbye"]],
            },
        ]
    ]
    if max_history is not None:
        expected_features = [x[-max_history:] for x in expected_features]

    assert actual_features is not None
    assert len(actual_features) == len(expected_features)

    for actual, expected in zip(actual_features, expected_features):
        assert compare_featurized_states(actual, expected)

"""

@pytest.mark.parametrize("max_history", [None, 2])
def test_prediction_states(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    max_history: Optional[int],
):

    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )
    actual_states = tracker_featurizer.prediction_states(
        [moodbot_tracker], moodbot_domain,
    )

    expected_states = [
        [
            {},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "greet"},
            },
            {USER: {INTENT: "greet"}, PREVIOUS_ACTION: {ACTION_NAME: "utter_greet"},},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "mood_unhappy"},
            },
            {
                USER: {INTENT: "mood_unhappy"},
                PREVIOUS_ACTION: {ACTION_NAME: "utter_cheer_up"},
            },
            {
                USER: {INTENT: "mood_unhappy"},
                PREVIOUS_ACTION: {ACTION_NAME: "utter_did_that_help"},
            },
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "deny"},
            },
            {USER: {INTENT: "deny"}, PREVIOUS_ACTION: {ACTION_NAME: "utter_goodbye"},},
        ]
    ]
    if max_history is not None:
        expected_states = [x[-max_history:] for x in expected_states]

    assert actual_states is not None
    assert len(actual_states) == len(expected_states)

    for actual, expected in zip(actual_states, expected_states):
        assert actual == expected


@pytest.mark.parametrize("max_history", [None, 2])
def test_prediction_states_hide_rule_states(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    max_history: Optional[int],
):

    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )

    rule_tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted("utter_greet", hide_rule_turn=True),
            ActionExecuted(ACTION_LISTEN_NAME, hide_rule_turn=True),
        ],
        domain=moodbot_domain,
    )

    actual_states = tracker_featurizer.prediction_states(
        [rule_tracker], moodbot_domain, ignore_rule_only_turns=True,
    )

    expected_states = [
        [
            {},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "greet"},
            },
        ],
    ]

    assert actual_states is not None
    assert len(actual_states) == len(expected_states)

    for actual, expected in zip(actual_states, expected_states):
        assert actual == expected

    embedded_rule_tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted("utter_greet", hide_rule_turn=True),
            ActionExecuted(ACTION_LISTEN_NAME, hide_rule_turn=True),
            user_uttered("mood_great"),
            ActionExecuted("utter_happy"),
            ActionExecuted(ACTION_LISTEN_NAME),
        ],
        domain=moodbot_domain,
    )

    actual_states = tracker_featurizer.prediction_states(
        [embedded_rule_tracker], moodbot_domain, ignore_rule_only_turns=True,
    )

    expected_states = [
        [
            {},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "mood_great"},
            },
            {
                USER: {INTENT: "mood_great"},
                PREVIOUS_ACTION: {ACTION_NAME: "utter_happy"},
            },
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "mood_great"},
            },
        ]
    ]

    if max_history is not None:
        expected_states = [x[-max_history:] for x in expected_states]

    assert actual_states is not None
    assert len(actual_states) == len(expected_states)

    for actual, expected in zip(actual_states, expected_states):
        assert actual == expected


@pytest.mark.parametrize("max_history", [None, 3])
def test_prediction_states_ignores_action_intent_unlikely(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    max_history: Optional[int],
):

    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )

    tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_greet"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("mood_great"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_happy"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("goodbye"),
        ],
        domain=moodbot_domain,
    )

    actual_states = tracker_featurizer.prediction_states(
        [tracker], moodbot_domain, ignore_action_unlikely_intent=True
    )

    expected_states = [
        [
            {},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "greet"},
            },
            {USER: {INTENT: "greet"}, PREVIOUS_ACTION: {ACTION_NAME: "utter_greet"},},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "mood_great"},
            },
            {
                USER: {INTENT: "mood_great"},
                PREVIOUS_ACTION: {ACTION_NAME: "utter_happy"},
            },
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "goodbye"},
            },
        ]
    ]

    if max_history is not None:
        expected_states = [x[-max_history:] for x in expected_states]

    assert actual_states is not None
    assert len(actual_states) == len(expected_states)

    for actual, expected in zip(actual_states, expected_states):
        assert actual == expected


@pytest.mark.parametrize("max_history", [None, 3])
def test_prediction_states_keeps_action_intent_unlikely(
    moodbot_tracker: DialogueStateTracker,
    moodbot_domain: Domain,
    max_history: Optional[int],
):

    state_featurizer = SingleStateFeaturizer()
    tracker_featurizer = MaxHistoryTrackerFeaturizer(
        state_featurizer, max_history=max_history
    )

    tracker = DialogueStateTracker.from_events(
        "default",
        [
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("greet"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_greet"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("mood_great"),
            ActionExecuted(ACTION_UNLIKELY_INTENT_NAME),
            ActionExecuted("utter_happy"),
            ActionExecuted(ACTION_LISTEN_NAME),
            user_uttered("goodbye"),
        ],
        domain=moodbot_domain,
    )

    actual_states = tracker_featurizer.prediction_states([tracker], moodbot_domain,)

    expected_states = [
        [
            {},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "greet"},
            },
            {
                USER: {INTENT: "greet"},
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_UNLIKELY_INTENT_NAME},
            },
            {USER: {INTENT: "greet"}, PREVIOUS_ACTION: {ACTION_NAME: "utter_greet"},},
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "mood_great"},
            },
            {
                USER: {INTENT: "mood_great"},
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_UNLIKELY_INTENT_NAME},
            },
            {
                USER: {INTENT: "mood_great"},
                PREVIOUS_ACTION: {ACTION_NAME: "utter_happy"},
            },
            {
                PREVIOUS_ACTION: {ACTION_NAME: ACTION_LISTEN_NAME},
                USER: {INTENT: "goodbye"},
            },
        ]
    ]

    if max_history is not None:
        expected_states = [x[-max_history:] for x in expected_states]

    assert actual_states is not None
    assert len(actual_states) == len(expected_states)

    for actual, expected in zip(actual_states, expected_states):
        assert actual == expected
